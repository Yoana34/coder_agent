# Architecture — MiniCoder

> 当前重要文件与职责地图。随实现持续更新。

## 项目结构（当前状态，随实现更新）

```
project/
├── minicoder/
│   ├── __init__.py
│   ├── cli.py            # argparse 入口 + Agent 接线 + 退出码
│   ├── config.py         # 配置加载：.env 自研解析 + 环境变量 + CLI 覆盖
│   ├── agent.py          # 主循环：消息组装→LLM→解析→工具执行→回传→终止
│   ├── llm.py            # DeepSeek 客户端（requests 直连，重试/退避/结构解析）
│   ├── mock_llm.py       # 离线确定性脚本化 mock（与 llm 同接口）
│   ├── mock_demo.py      # --mock 离线演示场景（读→修→跑→总结，真实执行工具）
│   ├── context.py        # ContextManager：整轮裁剪 + token 估算
│   ├── errors.py         # 异常体系（含 AgentLimitExceeded）
│   └── tools/
│       ├── __init__.py   # 注册表 + execute_tool 分发器 + 统一截断
│       ├── base.py       # Tool 基类 + OpenAI 函数 schema
│       ├── read_file.py  # 带行号读取
│       ├── write_file.py # 覆盖写入（自动建父目录）
│       └── run_command.py# shell 执行 + 超时杀进程
├── demo/                 # 演示场景：buggy_wordcount.py（bug 版，供 agent 修复）+ sample.txt
├── tests/                # pytest（conftest 处理 sys.path）
│   ├── conftest.py
│   ├── test_tools.py
│   ├── test_llm.py
│   ├── test_agent.py
│   ├── test_context.py
│   └── test_cli.py
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
