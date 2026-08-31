"""Agent 主循环 —— 项目核心。

循环：任务 → LLM 调用（附 tools）→ 输出解析 → 工具本地执行 → 结果回传 → 终止判断。
所有"重要逻辑"自研：输出解析（含坏 JSON 恢复）、循环终止条件、错误处理。

终止条件：
  1. 模型返回纯文本（无 tool_calls）→ 成功，返回该文本
  2. 达 max_iterations → 抛 AgentLimitExceeded
  3. LLM 连续失败（客户端已重试 3 次）→ 抛 LLMError
  4. Ctrl+C → KeyboardInterrupt 上抛，由 CLI 干净处理
"""

from __future__ import annotations

import json
from typing import Any

from .config import Config
from .context import ContextManager
from .errors import AgentLimitExceeded
from .llm import ChatResult, ToolCall
from .tools import execute_tool, tool_schemas

SYSTEM_PROMPT = """你是一个编程智能体（coding agent），运行在用户的本地电脑上。
你有一个隔离的工作区（workspace）：所有文件读写和命令执行都在工作区内进行，
越界（如访问工作区以外的文件）会被拒绝。
你可以通过工具完成编程任务：读取文件（read_file）、写入文件（write_file）、执行 shell 命令（run_command）。
这是多轮对话：完成一个任务后，用户可能继续提问或要求修改。
你要记住之前完成的工作，基于已有的上下文继续处理，不必重新探查已了解的信息。
工作方式：
1. 每轮要么调用一个或多个工具，要么直接给出最终回答。
2. 需要信息时先用工具探查（read_file / run_command），再决定下一步。
3. 修改代码后应运行命令验证结果。
4. 工具返回错误是正常现象：阅读错误信息，修正后重试。
5. 任务完成后，用纯文本给出最终总结，不要再调用工具。
避免不必要的破坏性操作。"""


class Agent:
    def __init__(self, cfg: Config, client: Any, echo: bool = True, workspace: str | None = None):
        self.cfg = cfg
        self.client = client
        self.echo = echo
        self.workspace = workspace  # 工作区根目录；None 表示不限制（测试用）
        self.ctx: ContextManager | None = None

    @property
    def messages(self) -> list[dict[str, Any]]:
        """当前对话历史（含 system + 初始 user），供测试/诊断读取。"""
        return self.ctx.messages if self.ctx else []

    # ---------- 对外入口 ----------

    def run(self, task: str) -> str:
        """执行一轮任务，返回最终回复。可多次调用形成多轮对话：上下文跨轮保留。

        未完成（达上限）抛 AgentLimitExceeded。
        """
        # 多轮对话：首次创建上下文，之后把用户追问追加进已有历史
        if self.ctx is None:
            self.ctx = ContextManager(self.cfg, SYSTEM_PROMPT, task)
        else:
            self.ctx.add_user_message(task)
        self._say(f"任务：{task}\n")

        for iteration in range(1, self.cfg.max_iterations + 1):
            self._say(f"━━━ 第 {iteration}/{self.cfg.max_iterations} 轮 ━━━")
            # 轮次边界统一裁剪，保持历史不超上限且协议合法
            self.ctx.trim()
            result = self.client.chat(self.ctx.to_list(), tools=tool_schemas())

            if result.tool_calls:
                self._handle_tool_calls(result)
                continue

            # 无工具调用 → 最终回复；写入历史，供后续追问参考
            final = (result.content or "").strip()
            self.ctx.append(result.message)
            self._say(f"\n✅ 完成\n{final}")
            return final

        raise AgentLimitExceeded(
            f"达到最大迭代轮数 {self.cfg.max_iterations} 仍未得到最终回答。"
        )

    # ---------- 内部：工具调用处理 ----------

    def _handle_tool_calls(self, result: ChatResult) -> None:
        # 1. 将完整 assistant 消息（含 tool_calls）追加到历史，保证 tool_call_id 可匹配
        self.ctx.append(result.message)
        if result.content:
            self._say(result.content)

        # 2. 逐条解析并执行工具，结果以 tool 角色回传
        for tc in result.tool_calls:
            args = self._parse_args(tc)
            if args is None:
                # 参数 JSON 解析失败：不执行工具，回传错误让模型重试
                error_content = (
                    f"[参数解析错误] 工具 {tc.name} 的参数不是合法 JSON: "
                    f"{tc.arguments_raw!r}。请修正后重新调用。"
                )
                self._say(f"  ⚠ {error_content}")
                self.ctx.append({"role": "tool", "tool_call_id": tc.id, "content": error_content})
                continue

            self._say(f"  → 调用 {tc.name} {json.dumps(args, ensure_ascii=False)[:160]}")
            output = execute_tool(self.cfg, tc.name, args, workspace=self.workspace)
            self._say(f"  ← {output[:300]}")
            self.ctx.append({"role": "tool", "tool_call_id": tc.id, "content": output})

    @staticmethod
    def _parse_args(tc: ToolCall) -> dict[str, Any] | None:
        """解析工具参数 JSON。成功返回 dict，失败返回 None。"""
        raw = tc.arguments_raw
        if not raw or not raw.strip():
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    # ---------- 内部：输出 ----------

    def _say(self, text: str) -> None:
        if self.echo:
            print(text)
