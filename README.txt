MiniCoder —— 编程智能体

一个让大语言模型真正“动手编程”的轻量级 Coding Agent，提供类似 Claude Code、Codex 的核心能力。用户通过自然语言描述编程任务，Agent 自主分析项目、读取和修改文件、执行命令并根据执行结果进行迭代，直至完成任务并给出结果总结。

【核心功能】

1. 自主编程
   基于 LLM 构建 Agent Loop，自主完成“任务分析 → 文件读取 → 代码修改 → 命令执行 → 结果分析 → 继续修复”的闭环。

2. 多轮交互
   任务完成后无需重启程序，可继续提出新的编程需求。对话历史保留，并通过滑动裁剪控制上下文长度，同时成对删除完整工具调用，避免产生孤立的 Tool 消息。

3. 工作区沙箱
   文件读写和命令执行均限定在独立 workspace 目录内，并进行路径越界检查，避免 Agent 误修改自身代码或访问工作区之外的文件。

4. 错误自恢复
   工具执行失败或模型返回非法 JSON 时，不直接终止程序，而是将错误信息反馈给模型，由 Agent 自主分析并尝试修正。

5. 可复现验证
   提供离线 Mock LLM 和 44 项单元测试，无需 API Key 或网络连接即可验证 Agent Loop、工具调用、错误处理等核心功能。

【运行方式】

环境要求：Python 3.10+

1. 安装依赖
   pip install -r requirements.txt

2. 离线演示（无需 API Key）
   python -m minicoder.cli --mock

3. 使用真实 LLM
   复制 .env.example 为 .env，填入 DeepSeek API Key，然后执行：
   python -m minicoder.cli

将待处理的项目文件放入 workspace 目录，在终端输入自然语言编程任务即可。

4. 运行测试
   python -m pytest

【仓库地址】

https://github.com/Yoana34/coder_agent
