# Architecture — MiniCoder

> 当前重要文件与职责地图。随实现持续更新。

## 项目结构（当前状态，随实现更新）

```
project/
├── minicoder/            # 核心代码
│   ├── __init__.py
│   ├── cli.py            # argparse 入口 + Agent 接线 + 退出码
│   ├── config.py         # 配置加载：.env 自研解析 + 环境变量 + CLI 覆盖
│   ├── agent.py          # 主循环：消息组装→LLM→解析→工具执行→回传→终止
│   ├── llm.py            # DeepSeek 客户端（requests 直连，重试/退避/结构解析）
│   ├── mock_llm.py       # 离线确定性脚本化 mock（与 llm 同接口）
│   ├── mock_demo.py      # --mock 离线演示场景（读→修→跑→总结，真实执行工具）
│   ├── seed_demo.py      # 把 demo/ 模板复制到工作区（已存在则不覆盖）
│   ├── context.py        # ContextManager：整轮裁剪 + token 估算
│   ├── errors.py         # 异常体系（含 AgentLimitExceeded）
│   └── tools/
│       ├── __init__.py   # 注册表 + execute_tool 分发器 + 统一截断 + 工作区沙箱
│       ├── base.py       # Tool 基类 + OpenAI 函数 schema
│       ├── read_file.py  # 带行号读取
│       ├── write_file.py # 覆盖写入（自动建父目录）
│       └── run_command.py# shell 执行 + 超时杀进程
├── demo/                 # 演示场景模板：buggy_wordcount.py（bug 版）+ sample.txt
├── workspace/            # agent 工作区（沙箱，gitignore，运行自动创建）
├── tests/                # pytest（37 项）
│   ├── conftest.py       # sys.path 处理
│   ├── run_tests.bat     # 一键跑测试（内置 PYTHONNOUSERSITE）
│   ├── test_tools.py     # 含 8 项工作区沙箱测试（越界拦截/默认 cwd）
│   ├── test_llm.py
│   ├── test_agent.py
│   ├── test_context.py
│   └── test_cli.py
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── CLAUDE.md
└── memory-bank/          # 设计/技术栈/计划/进度/架构
```

## 核心数据流

```
用户任务 → [context.py 组装 messages]
         → [llm.py 调 DeepSeek /chat/completions (tools 附带)]
         → [agent.py 解析响应]
              ├─ tool_calls → [tools/ 注册表本地执行，路径经工作区沙箱校验]
              │     越界路径（../、其他盘符）→ 拒绝并回传 `路径越界` → 循环
              └─ 纯文本 → 打印 → 终止
```

> 沙箱：`agent` 持有 `workspace` 根目录；`execute_tool(..., workspace=...)` 在分发前把
> `read_file`/`write_file` 的 `path` 与 `run_command` 的 `cwd` 解析到工作区内，
> 越界抛 `ToolError` 转成错误字符串回传模型。运行前 `seed_demo()` 把 `demo/` 模板复制进工作区。
