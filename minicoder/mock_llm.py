"""离线确定性 mock LLM。

与 DeepSeekClient 实现同一接口（chat() -> ChatResult），但按预设脚本返回，无需网络与 API key。
用于：单元测试（验证 agent 循环行为）、无 key 时的离线演示。

脚本格式：list[dict]
  {"type": "final", "content": "..."}                          → 返回纯文本
  {"type": "tools", "tool_calls": [{"name":..., "arguments": dict|str}],
   "content": "可选前置文本"}                                  → 返回工具调用

arguments 传 dict 会正常 JSON 化；传 str 则原样放入（用于模拟坏 JSON，测试解析恢复）。
"""

from __future__ import annotations

import json
from typing import Any

from .errors import LLMError
from .llm import ChatResult, ToolCall


class MockLLM:
    def __init__(self, script: list[dict[str, Any]]):
        self.script = list(script)
        self.calls = 0

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> ChatResult:
        if self.calls >= len(self.script):
            raise LLMError("mock 脚本已用完")
        step = self.script[self.calls]
        self.calls += 1

        if step["type"] == "final":
            content = step.get("content", "")
            return ChatResult(
                content=content,
                tool_calls=None,
                message={"role": "assistant", "content": content},
            )

        # type == "tools"
        tool_calls: list[ToolCall] = []
        message_tool_calls: list[dict[str, Any]] = []
        for i, tc in enumerate(step["tool_calls"]):
            cid = tc.get("id") or f"call_{self.calls}_{i}"
            args = tc["arguments"]
            if isinstance(args, str):
                args_raw = args
            else:
                args_raw = json.dumps(args, ensure_ascii=False)
            tool_calls.append(ToolCall(id=cid, name=tc["name"], arguments_raw=args_raw))
            message_tool_calls.append(
                {"id": cid, "type": "function", "function": {"name": tc["name"], "arguments": args_raw}}
            )

        content = step.get("content")
        return ChatResult(
            content=content,
            tool_calls=tool_calls,
            message={"role": "assistant", "content": content, "tool_calls": message_tool_calls},
        )
