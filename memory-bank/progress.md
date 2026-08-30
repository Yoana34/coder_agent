# Progress — MiniCoder

> 执行日志（非设计文档）。每完成一步追加一条记录。

## 2026-08-30 — Bootstrap
- [x] 确认需求：Python + DeepSeek + 核心闭环 + CLI/demo/README 交付物
- [x] 完成 `memory-bank/design-document.md`（范围、架构、工具、解析、终止、边界、验收标准）
- [x] 完成 `memory-bank/tech-stack.md`
- [x] 完成 `memory-bank/implementation-plan.md`（Step 1–8）
- [x] 建立 `memory-bank/` + `CLAUDE.md` 记忆规则
- [x] Step 1 项目骨架与配置加载
  - 完成 `minicoder/__init__.py`、`config.py`（.env 自研解析 + 环境变量 + CLI 覆盖）、`errors.py`、`cli.py`（argparse 骨架 + 配置校验）、`requirements.txt`、`.env.example`
  - 验证：import OK；`--help` 正常；无 key 报错退出码 2；`--mock` 正常
- [x] Step 2 工具框架与三个工具
  - 完成 `tools/base.py`（Tool 基类 + schema）、`read_file.py`、`write_file.py`、`run_command.py`、`tools/__init__.py`（注册表 + execute_tool 分发器 + 统一截断）
  - `tests/test_tools.py` 12 项全部通过（含超时杀进程、坏参数兜底、截断）
  - **环境注意**：conda py312 会泄漏系统 Python 用户 site-packages（残缺 anyio/sniffio），测试/运行需加 `PYTHONNOUSERSITE=1`；后续 README 记录
- [x] Step 3 LLM 客户端
  - `llm.py`：requests 直连 /chat/completions 非流式；指数退避重试（429/5xx）；网络错误重试；认证等 4xx 快速失败；`_parse` 结构解析
  - `mock_llm.py`：确定性脚本化 mock，与 DeepSeekClient 同接口（chat() -> ChatResult）
  - `tests/test_llm.py` 7 项通过（含重试、快速失败、mock 序列、脚本耗尽）
- [x] Step 4 Agent 主循环
  - `agent.py`：循环 = 消息组装 → LLM(附 tools) → 输出解析 → 工具执行 → tool 回传；终止条件（最终回复/上限/Ctrl+C）；坏 JSON 参数回传错误恢复
  - `errors.py` 新增 `AgentLimitExceeded`
  - `tests/test_agent.py` 4 场景通过（完成/达上限/坏 JSON 恢复/Ctrl+C）
  - **全部 23 项测试通过** → 核心闭环（循环+三工具+终止+错误处理）能力达成
- [x] Step 5 上下文管理
  - `context.py`：ContextManager（system+user 常驻 + 尾部滑动窗口）；**整轮裁剪**保证协议合法；`estimate_tokens` 粗估
  - Agent 接入 ContextManager，轮次边界统一 trim；`agent.messages` 改为属性
  - `tests/test_context.py` 4 项通过（含协议合法性断言、无孤儿 tool 消息）
- [x] Step 6 CLI 完善与离线演示
  - `cli.py` 重写：接入 Agent，退出码（0 成功/1 未完成/2 配置/3 LLM/130 中断），`--cwd`，无 key 提示
  - `mock_demo.py`：离线演示脚本（真实执行工具，真实修复 demo 文件）；`demo/` 场景（buggy_wordcount.py bug 修复：split(" ")→split()，9→11）
  - 端到端验证通过：`--mock` 4 轮收敛读→修→跑→总结 exit 0；demo 文件验证后已恢复 buggy 版
  - `tests/test_cli.py` 2 项通过；**全部 29 项测试通过**
- [x] Step 7 Demo 场景与 README
  - `README.md`：简介/快速开始(mock+真实API)/配置/架构/测试/亮点/项目结构/提交物
  - `tests/run_tests.bat`：一键跑测试（内置 PYTHONNOUSERSITE，纯 ASCII 避免乱码）
  - demo 场景确认保持 bug 版（输出 9，可反复演示修复）
  - 验证：README 步骤可复现；**29 项测试通过**
- [ ] Step 8 真实 API 冒烟（可选，需 DEEPSEEK_API_KEY）
