# CLAUDE.md — MiniCoder 项目

从零实现的编程智能体（coding agent），核心逻辑全部自研，不依赖任何 agent 框架/SDK。

## 记忆规则

- 写任何代码前必须完整阅读 `memory-bank/architecture.md`
- 写任何代码前必须完整阅读 `memory-bank/design-document.md`
- 每完成一个重大功能或里程碑后，必须更新 `memory-bank/architecture.md`

## 运行方式

- 入口：`python -m minicoder.cli`（详见 README）
- 无 API key 时可用 `--mock` 离线演示
- 测试：`python -m pytest`

## 硬性约束（考核要求，不得违反）

- 禁止 agent 框架 / SDK（LangChain、LlamaIndex、OpenAI Agents SDK、Claude Agent SDK、AutoGen、CrewAI 等）
- 禁止依赖服务端托管的代码执行 / 文件工具（Code Interpreter、Files API）
- 对话历史与上下文管理、工具定义与本地执行、模型输出解析、循环终止条件、错误处理必须自研
