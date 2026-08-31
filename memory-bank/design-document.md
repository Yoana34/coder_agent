# 设计文档 — MiniCoder 编程智能体

> 推免考核项目 · 从零实现的核心逻辑编码 agent
> 状态：bootstrap 阶段，目标为「核心闭环」，后续可迭代

## 1. 范围与目标

### 目标
交付一个可运行的 CLI 编程智能体：用户在终端用自然语言描述编程任务，agent 通过与 DeepSeek LLM 对话，自主调用本地工具（读文件、写文件、执行命令）完成任务并输出结果。

### 非目标（v1 核心闭环）
- ❌ 不实现流式输出（v2 迭代）
- ❌ 不做对话历史摘要压缩（v2：token 裁剪先做简单版）
- ❌ 不做精准 diff 编辑 `edit_file`（v2）
- ❌ 不做交互式用户确认（v2）
- ❌ 不依赖任何 agent 框架 / SDK
- ❌ 不依赖 API 服务端托管代码执行（Code Interpreter / Files API）

### 必须自研的核心逻辑（考核硬性要求）
1. 对话历史与上下文管理
2. 工具的定义与本地执行
3. 模型输出的解析
4. 循环终止条件
5. 错误处理

## 2. 用户旅程

```
用户: 输入任务，如 "看看 demo 目录下的程序有什么 bug，修好它"
   ↓
Agent 执行该任务（内部循环，最多 max_iterations 轮）:
  1. Agent 组装 messages（system + 用户任务 + 历史 + 工具结果）
  2. 调用 DeepSeek chat completions（携带 tools 定义）
  3. 模型返回:
     ├─ 含 tool_calls → 逐条解析 → 本地执行 → 结果以 tool 角色回传 → 继续
     └─ 纯文本最终回复 → 打印给用户 → 该任务完成
   ↓
多轮对话: 不退出，提示"继续对话"，用户可接着提问/要求修改
   ↓
Agent 把追问作为新 user 消息追加进同一份历史，跨轮保留上下文继续执行
   ↓
空行或 退出/exit 结束会话
终止: 模型给出最终回复 / 达最大轮数 / Ctrl+C / API 连续失败
```

## 3. 架构

```
cli.py          argparse 入口，读取配置，启动 agent，Ctrl+C 处理
agent.py        主循环：消息组装 → LLM 调用 → 输出解析 → 工具分发 → 结果回传 → 终止判断
llm.py          DeepSeek OpenAI 兼容客户端（requests 直连 /chat/completions，非流式）
context.py      对话历史管理：消息追加、窗口裁剪、工具输出截断
tools/base.py   Tool 抽象基类 + 参数 schema 定义
tools/read_file.py   read_file  工具
tools/write_file.py  write_file 工具
tools/run_command.py run_command 工具
tools/__init__.py    工具注册表（TOOL_REGISTRY）+ execute_tool 分发器
errors.py       自定义异常（LLMError / ToolError / AgentTerminated）
```

**关键设计决策：**
- **不用 `openai` SDK，直接用 `requests` 调 HTTP**：展示对协议层的理解，零额外依赖（requests 已装），也彻底规避"框架/SDK"争议。
- **同步阻塞式设计**：LLM 调用和子进程执行都是阻塞的，同步代码最简单可靠，核心闭环不需要并发。
- **工具为声明式注册**：每个工具是一个类，携带 name/description/parameters(JSON Schema)，序列化为 OpenAI `tools` 参数；新增工具只需加一个文件。
- **上下文默认不裁剪整轮，而是截断**：工具输出超长时截断（默认 8000 字符），消息列表超上限（默认 30 条）时丢弃最老的工具结果消息。v2 再做摘要。
- **工作区沙箱（workspace）**：agent 默认在 `<cwd>/workspace/` 内读写与执行命令，防止误改 minicoder 自身代码或用户其他文件。`read_file` / `write_file` 的 `path` 与 `run_command` 的 `cwd` 都必须解析到工作区内，越界返回 `[工具错误] 路径越界`。demo 场景以模板形式存于 `demo/`，运行前由 `seed_demo()` 复制进工作区。
- **多轮对话（上下文管理的外部体现）**：agent 完成一个任务后不退出，CLI 进入"继续对话"循环；追问作为新 `user` 消息追加进同一份历史，`ContextManager` 跨轮保留——初始任务常驻头部，后续追问进入滑动窗口，整轮工具轮次优先被裁剪。系统提示词明确要求模型记住已完成的工作、基于上下文继续处理，使"上下文管理"在真实交互中可被观察。

## 4. 工具定义

| 工具 | 参数 | 行为 |
|---|---|---|
| `read_file` | `path: str`, `offset: int=0`, `limit: int=2000` | 读取文件内容；错误时返回带错误信息的字符串 |
| `write_file` | `path: str`, `content: str` | 覆盖写入文件（自动建父目录） |
| `run_command` | `command: str`, `timeout: int=30`, `cwd: str|None` | 用 shell 执行，返回 exit_code + 截断后的 stdout/stderr |

所有工具：
- 失败**不抛异常到模型**，而是返回结构化错误字符串给模型，让模型有机会自我修正。
- 输出统一截断，防止撑爆上下文。

## 5. 模型输出解析（核心逻辑）

非流式响应 `choices[0].message`：
- 若含 `tool_calls[]`：对每条取 `id` / `function.name` / `function.arguments`。
  - `arguments` 是 JSON 字符串，用 `json.loads` 解析；**解析失败时**向模型回传一条 `tool` 角色的错误消息（说明哪个参数无法解析），让模型重发，而不是崩溃。
- 若为纯文本：该文本即最终回复，终止循环。

结果回传格式（OpenAI/DeepSeek 兼容协议）：
```
messages.append({"role": "assistant", "content": <assistant content>, "tool_calls": [...]})
messages.append({"role": "tool", "tool_call_id": <id>, "content": <工具执行结果>})
```

## 6. 循环终止条件

| 条件 | 行为 |
|---|---|
| 模型返回纯文本回复 | 打印并成功退出 |
| 达到 `max_iterations`（默认 15） | 打印"已达最大轮数"并失败退出（非 0） |
| 用户 Ctrl+C | 打印提示，干净退出 |
| 同一轮内全部工具调用失败 | 仍回传错误，模型可重试；累计失败由 max_iterations 兜底 |
| LLM API 持续错误（超时/认证/限流） | 指数退避重试 3 次，仍失败则报错退出 |

## 7. 配置（环境变量 / CLI 参数）

| 项 | 环境变量 | 默认值 |
|---|---|---|
| API Key | `DEEPSEEK_API_KEY` | 无（缺失时报错提示） |
| 模型 | `MINICODER_MODEL` | `deepseek-chat` |
| Base URL | `MINICODER_BASE_URL` | `https://api.deepseek.com` |
| 最大轮数 | `MINICODER_MAX_ITERATIONS` | `15` |
| CLI 覆盖 | `--max-iterations` / `--model` / `--mock` / `--workspace` / `--seed-demo` | — |

- `--mock`：使用内置 mock LLM（离线、确定性），用于无 key 时的演示与测试。
- `--workspace <目录>`：agent 工作区（默认 `<cwd>/workspace`），越界读写被拒。
- `--seed-demo`：把 `demo/` 模板复制进工作区（`--mock` 自动执行）。
- `.env.example` 提供配置模板；本地加载 `.env`（若存在）。

## 8. 状态与数据模型

- **对话历史**：`list[dict]`，OpenAI chat 消息格式（system / user / assistant / tool）。
- **工具调用记录**：保留 assistant.tool_calls 原样 + tool 角色结果，保证协议完整。
- **多轮对话历史**：同一 `ContextManager` 跨轮存活；每轮任务的最终 assistant 回复也写入历史，供后续追问参考。
- **无持久化**：v1 不落盘会话，进程退出即清空（会话内跨轮保留）。

## 9. 边界与异常场景

| 场景 | 处理 |
|---|---|
| API key 缺失 | 启动时清晰报错，提示设置环境变量或用 `--mock` |
| 网络/限流 | 指数退避重试 3 次 |
| 文件不存在 | `read_file` 返回错误字符串给模型 |
| 命令超时 | `run_command` 杀进程，返回 exit_code=124 + 提示 |
| 命令输出超长 | 截断到上限，附 `[truncated]` 标记 |
| 工具参数 JSON 解析失败 | 回传错误给模型重试 |
| 无 key 且无 mock | 报错退出，不静默 |
| 工具路径越出工作区（`../`、绝对路径、其他盘符） | 沙箱拦截，返回 `路径越界` 错误字符串给模型 |

## 10. 验收标准（acceptance criteria）

1. `python -m minicoder.cli --help` 正常输出。
2. 无 API key 时 `--mock` 模式能完成一次"读文件→改文件→跑命令→收尾"的完整循环并给出最终回复。
3. 有 API key 时，对 demo 任务（修一个 bug）能自主完成：读文件 → 定位 → 修改 → 运行验证 → 总结。
4. 达 `--max-iterations` 轮仍无最终回复时，干净退出并提示。
5. 多轮对话：完成任务后可继续追问，历史跨轮保留；空行 / `退出` / `exit` 结束会话。
6. 单元测试覆盖：工具执行、输出解析、终止条件（含坏 JSON 参数恢复）、上下文裁剪、多轮对话上下文保留、REPL 行为。
