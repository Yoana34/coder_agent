# MiniCoder — 从零实现的编程智能体

> 软件工程专业推免（南大）考核项目。个人独立实现一个简化版 Claude Code / Codex：
> 通过与 LLM 对话，自主读写文件、执行命令，完成编程任务。

**核心要求达成：核心逻辑全部自研，零 agent 框架 / SDK 依赖。**

- 对话历史与上下文管理 ✅（`context.py`）
- 工具的定义与本地执行 ✅（`tools/`）
- 模型输出的解析 ✅（`agent.py`，含坏 JSON 恢复）
- 循环终止条件 ✅（`agent.py`）
- 错误处理 ✅（`errors.py` + 各层兜底）

## 环境准备

推荐用专用 conda 环境（已内置 `PYTHONNOUSERSITE=1`，避免本机用户级 site-packages 污染）：

```bash
conda create -n minicoder -y --override-channels \
  -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main \
  -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free \
  python=3.12 requests pytest
conda env config vars set PYTHONNOUSERSITE=1 -n minicoder   # 内置环境变量
conda activate minicoder
```

> 说明：默认 `defaults` 频道指向 `repo.anaconda.com`，国内常不可达；用清华镜像可正常安装。
> `anyio`/`sniffio` 若缺失（pytest 依赖），执行 `pip install anyio sniffio`。

## 快速开始

### 方式一：离线演示（无需 API key）

```bash
python -m minicoder.cli --mock
```

启动后会自动跑一遍完整闭环：**读取工作区中带 bug 的程序 → 定位问题 → 写入修复 → 运行验证 → 总结**。

### 方式二：真实 DeepSeek API

1. 在 [DeepSeek 开放平台](https://platform.deepseek.com) 注册并创建 API key。
2. 复制 `.env.example` 为 `.env`，填入 `DEEPSEEK_API_KEY`（或直接设置环境变量）。
3. 用 `--seed-demo` 把演示场景复制进工作区，然后运行：

```bash
python -m minicoder.cli --seed-demo "buggy_wordcount.py 的单词统计有 bug，请修复并验证"
```

### 常见参数

| 参数 | 说明 |
|---|---|
| `--mock` | 离线确定性演示（不调用 API，自动 seed 工作区） |
| `--workspace <目录>` | agent 工作区（默认 `<当前目录>/workspace`），越界读写被拒 |
| `--seed-demo` | 把 `demo/` 模板复制到工作区（已存在则不覆盖） |
| `--model <名>` | 覆盖模型名（默认 `deepseek-chat`） |
| `--max-iterations <n>` | 最大迭代轮数（默认 15） |
| `--cwd <目录>` | 先切换工作目录再执行 |

退出码：`0` 成功 / `1` 未完成（达上限）/ `2` 配置错误 / `3` LLM 错误 / `130` 用户中断。

## 工作区沙箱（安全设计）

agent 默认在 `<cwd>/workspace/` 内读写文件与执行命令：

- `read_file` / `write_file` 的 `path`、`run_command` 的 `cwd` 必须解析到工作区内；
- 越界访问（`../`、绝对路径、其他盘符）返回 `路径越界` 错误字符串给模型，模型可自行修正；
- `run_command` 默认在 `workspace/` 下执行，无法用命令逃逸；
- `demo/` 只作为任务模板源，agent 永远不会修改它；`workspace/` 已 gitignore，不入库。

这样即使模型犯错，也无法改动 minicoder 自身代码或你的其他文件。

## 配置（环境变量 / `.env`）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 无 | 必填（除非 `--mock`），勿提交 `.env` |
| `MINICODER_MODEL` | `deepseek-chat` | 模型名 |
| `MINICODER_BASE_URL` | `https://api.deepseek.com` | OpenAI 兼容端点，可切换 |
| `MINICODER_MAX_ITERATIONS` | `15` | 最大轮数 |
| `MINICODER_MAX_MESSAGES` | `30` | 历史滑动窗口上限 |
| `MINICODER_TOOL_OUTPUT_LIMIT` | `8000` | 工具输出截断长度 |

## 运行测试

```bash
conda activate minicoder   # 已内置 PYTHONNOUSERSITE=1，直接跑即可
python -m pytest tests/ -v
```

37 项测试全部通过，覆盖：工具执行、超时杀进程、LLM 重试、主循环四场景、上下文裁剪协议合法性、工作区沙箱（越界拦截）、CLI 端到端。

## 架构

```
任务 ──→ [context.py] 组装消息
      ──→ [llm.py] DeepSeek /chat/completions（附 tools，非流式）
      ──→ [agent.py] 解析响应
             ├─ 有 tool_calls → [tools/ 注册表] 本地执行
             │     read_file / write_file / run_command
             │     └─ 结果以 tool 角色回传 → 继续循环
             └─ 纯文本 → 打印 → 终止（成功）
终止：模型最终回复 / 达 max_iterations / Ctrl+C / LLM 连续失败
```

| 模块 | 职责 |
|---|---|
| `cli.py` | 参数解析、配置校验、退出码、中断处理 |
| `config.py` | 环境变量 + `.env`（自研解析器）+ CLI 覆盖 |
| `agent.py` | 主循环：消息组装 → LLM → 解析 → 工具执行 → 回传 → 终止 |
| `llm.py` | requests 直连 API，指数退避重试，响应结构解析 |
| `context.py` | 历史滑动窗口：整轮裁剪保持协议合法，token 粗估 |
| `tools/` | 声明式工具注册表 + 三个本地工具（读/写/命令） |
| `mock_llm.py` / `mock_demo.py` | 离线确定性演示（真实执行工具） |

## 设计要点（考核亮点）

- **协议级理解**：不用 `openai` SDK，用 `requests` 直连 `/chat/completions`，完整实现 `tools` / `tool_calls` / `tool` 角色回传协议。
- **工具失败不崩溃**：错误作为字符串回传模型，模型可自我修正（坏 JSON 参数同样回传错误重试）。
- **工作区沙箱**：agent 只能在工作区内读写/执行命令，越界路径被拦截——自研路径解析与越界校验，保护 minicoder 自身代码不被误改。
- **上下文裁剪保证协议合法**：成对删除整轮 `assistant(tool_calls) + tool`，杜绝孤儿 tool 消息。
- **确定性测试**：mock LLM 使主循环可在离线可复现地验证（完成/达上限/坏 JSON 恢复/中断）。

## 项目结构

```
minicoder/          # 核心代码
tools/              # 工具注册表 + 沙箱 + read_file / write_file / run_command
workspace/          # agent 工作区（沙箱，gitignore，运行自动创建）
tests/              # 37 项 pytest
demo/               # 演示场景模板（带 bug 的 wordcount 程序 + 样例文本）
memory-bank/        # 设计文档 / 技术栈 / 实施计划 / 进度 / 架构
```

## 提交物

- **Git 仓库**：本仓库（公开，完整提交历史）。
- **README.txt**：≤1000 字，含仓库地址、运行方式、特色功能（提交时填写）。
- **视频**：≤2 分钟 mp4，演示 agent 完成真实编程任务（建议用真实 API 跑 demo 场景）。
