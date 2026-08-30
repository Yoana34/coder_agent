# 实施计划 — MiniCoder（核心闭环）

> 从 `design-document.md` + `tech-stack.md` 推导。每一步：小、具体、有序、可独立验证。
> 规则：`implementation-plan.md` 不含代码；每一步验证通过后才能进入下一步。

## Step 1 — 项目骨架与配置加载
- 创建包结构：`minicoder/`（含 `__init__.py`）、`minicoder/tools/`（含 `__init__.py`）
- 创建 `requirements.txt`（requests、pytest）
- 创建 `.env.example`（DEEPSEEK_API_KEY / MINICODER_MODEL / MINICODER_BASE_URL / MINICODER_MAX_ITERATIONS）
- 实现配置加载：读环境变量 + 可选 `.env` 文件，提供默认值；缺失 API key 时报清晰错误
- 实现 `minicoder/cli.py` 的 argparse 骨架（`--model` / `--max-iterations` / `--mock` / `--help`）

**验证：**
- `python -c "import minicoder"` 无报错
- `python -m minicoder.cli --help` 输出参数说明且正常退出
- 无 key 时启动报"缺少 DEEPSEEK_API_KEY，或用 --mock"

## Step 2 — 工具框架与三个工具
- `minicoder/tools/base.py`：Tool 基类（name/description/参数 JSON Schema/run 方法）
- `minicoder/tools/read_file.py`、`write_file.py`、`run_command.py`
- `minicoder/tools/__init__.py`：注册表 + `execute_tool(name, args)` 分发器，未知工具/参数错误返回错误字符串
- `minicoder/errors.py`：异常定义
- 工具输出统一截断（长输出加 `[truncated]` 标记）

**验证（pytest）：**
- read_file 正常读、文件不存在返回错误字符串
- write_file 覆盖写入、自动建父目录
- run_command 返回 exit_code/stdout/stderr；命令超时被杀；输出超长被截断
- execute_tool 对未知工具名返回错误而非抛异常

## Step 3 — LLM 客户端
- `minicoder/llm.py`：用 requests 调 DeepSeek `/chat/completions`（非流式）
- 入参：messages + tools（可选）；返回：结构化响应（content + tool_calls）
- 错误处理：超时/认证/限流 → 指数退避重试 3 次 → 抛 LLMError
- `minicoder/mock_llm.py`：确定性 mock 客户端（按预设脚本依次返回 tool_calls → 最终文本）

**验证（pytest）：**
- 用 monkeypatch 伪造 HTTP 响应：正常返回含 tool_calls 的响应
- 模拟 401 / 限流：触发重试与最终 LLMError
- mock 客户端返回符合预期的序列

## Step 4 — Agent 主循环
- `minicoder/agent.py`：Agent 类，实现循环
  - 组装 system + 用户任务 + 历史
  - 调 LLM → 解析输出 → 有 tool_calls 则本地执行 → 以 `tool` 角色回传 → 继续
  - 纯文本 → 打印并返回成功
- 输出解析：`function.arguments` 为 JSON 字符串，解析失败时回传 `tool` 角色错误消息让模型重发
- 终止条件：max_iterations 达成 → 报错退出；`--mock` 下可离线跑通完整循环
- Ctrl+C 优雅退出

**验证（pytest，用 mock LLM）：**
- 场景 A：任务完成（读→写→跑→最终回复）→ 返回成功
- 场景 B：模型一直发 tool_calls 不收敛 → 达 max_iterations 报错
- 场景 C：坏 JSON 参数 → 回传错误 → 模型重发正确参数 → 完成
- 场景 D：Ctrl+C → 干净退出

## Step 5 — 上下文管理
- `minicoder/context.py`：消息追加、工具输出截断、消息窗口裁剪（超上限丢最老工具消息）
- 暴露 `estimate_tokens` 或等效的消息计数，供裁剪判断

**验证（pytest）：**
- 历史超上限时最老工具消息被丢弃、system 消息保留
- 长工具输出被截断且带标记
- 裁剪后协议仍合法（tool 结果对应的 assistant.tool_calls 若被裁剪则一并处理）

## Step 6 — CLI 完善与离线演示
- `cli.py` 完整接线：交互式提示、任务参数、结果输出、退出码
- `--mock` 模式下跑通一次完整 demo 任务

**验证：**
- 无 key 运行 `python -m minicoder.cli --mock "演示任务"` 完整走通"读→写→跑→总结"
- 退出码符合预期（成功 0 / 未完成非 0）

## Step 7 — Demo 场景与 README
- 创建 `demo/`：一个带 bug 的小型 Python 程序 + 任务说明（供 agent 修）
- 编写 `README.md`：项目简介、架构图、快速开始、`--mock` 演示、真实 API 用法、考核亮点
- 补充 `AGENTS.md`/`CLAUDE.md` 记忆规则（见工作流）

**验证：**
- `--mock` 在 demo 上端到端跑通
- 有真实 key 时对 demo 任务跑通（若 key 可用）
- README 步骤照做即可复现

## Step 8（可选）— 真实 API 冒烟
- 有 `DEEPSEEK_API_KEY` 时，对 demo 任务做真实冒烟，确认真实模型表现与超参合理

**验证：**
- 真实模型完成 demo 任务并自验（跑测试/命令确认修复有效）

---

## 里程碑 checkpoint
- 完成 Step 4（主循环）后：核心能力达成，若用户希望 git 提交可在此建 checkpoint
- 完成 Step 7 后：可交付考核
