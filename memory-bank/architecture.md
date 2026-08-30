# Architecture — MiniCoder

> 当前重要文件与职责地图。随实现持续更新。

## 项目结构（当前状态，随实现更新）

```
project/
├── minicoder/
│   ├── __init__.py
│   ├── cli.py            # argparse 入口（Step1: 骨架+配置校验）
│   ├── config.py         # 配置加载：.env 自研解析 + 环境变量 + CLI 覆盖
│   ├── agent.py          # 主循环：消息组装→LLM→解析→工具执行→回传→终止
│   ├── llm.py            # DeepSeek 客户端（requests 直连，重试/退避/结构解析）
│   ├── mock_llm.py       # 离线确定性脚本化 mock（与 llm 同接口）
│   ├── context.py        # 上下文管理（待实现）
│   ├── errors.py         # 异常体系（含 AgentLimitExceeded）
│   └── tools/
│       ├── __init__.py   # 注册表 + execute_tool 分发器 + 统一截断
│       ├── base.py       # Tool 基类 + OpenAI 函数 schema
│       ├── read_file.py  # 带行号读取
│       ├── write_file.py # 覆盖写入（自动建父目录）
│       └── run_command.py# shell 执行 + 超时杀进程
├── tests/                # pytest（conftest 处理 sys.path）
│   ├── conftest.py
│   ├── test_tools.py
│   ├── test_llm.py
│   └── test_agent.py
├── demo/                 # 演示场景
├── tests/                # pytest
├── README.md
├── requirements.txt
├── .env.example
├── CLAUDE.md / AGENTS.md
└── memory-bank/
```

## 核心数据流

```
用户任务 → [context.py 组装 messages]
         → [llm.py 调 DeepSeek /chat/completions (tools 附带)]
         → [agent.py 解析响应]
              ├─ tool_calls → [tools/ 注册表本地执行] → 结果以 tool 角色回传 → 循环
              └─ 纯文本 → 打印 → 终止
```
