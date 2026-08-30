# 技术栈 — MiniCoder

> 从 `design-document.md` 推导，原则：简单、稳健、够用即可。

## 选型

| 层 | 选择 | 理由 |
|---|---|---|
| 语言 | Python 3.12 | 环境现成（conda/Python312），工具生态成熟 |
| HTTP 客户端 | `requests`（已安装） | 直连 DeepSeek `/chat/completions`，零新依赖，展示协议层理解 |
| 模型 API | DeepSeek（OpenAI 兼容 /chat/completions，非流式） | 国产、便宜、OpenAI 兼容；题目中提及 DeepSeek Harness，作为对标合理 |
| CLI | `argparse`（标准库） | 无需 click/typer 等额外依赖，参数简单够用 |
| 工具执行 | `subprocess` / `pathlib` / `os`（标准库） | 本地命令执行与文件读写 |
| 配置 | 环境变量 + 可选 `.env` + 可选 `--mock` | 简单，支持无 key 离线演示 |
| 测试 | `pytest` + 内置 mock LLM | 离线确定性验证核心闭环，不依赖真实 API |
| 打包/部署 | 无（源码直跑 `python -m minicoder.cli`） | 考核交付，无需安装部署链 |

## 明确不使用

- ❌ 任何 agent 框架 / SDK：LangChain、LlamaIndex、OpenAI Agents SDK、Claude Agent SDK、AutoGen、CrewAI
- ❌ `openai` 客户端库（可选但不用——直连 HTTP 更透明、无争议）
- ❌ 服务端托管工具（Code Interpreter / Files API）
- ❌ 流式（v2）、消息摘要（v2）

## 运行时依赖（requirements.txt）

```
requests>=2.31        # 唯一运行时依赖（已装）
pytest>=7.0           # 开发/测试
```

## 兼容性说明

- DeepSeek 完全兼容 OpenAI `chat/completions` 协议（含 `tools` / `tool_calls` / `tool` 角色回传）。
- `MINICODER_BASE_URL` 可配置，未来可切任意 OpenAI 兼容端点（通义/月之暗面等）而不改代码。
