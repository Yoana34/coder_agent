"""上下文管理：对话历史的追加、窗口裁剪与 token 估算。

裁剪策略（v1 滑动窗口）：
- 永远保留前 2 条（system + 初始 user 任务）。
- 超上限时，成对删除最旧的"完整工具轮次"（一条带 tool_calls 的 assistant 消息
  + 紧随其后的全部 tool 消息）。整轮删除保证协议合法：每条 tool 消息都能
  与 assistant.tool_calls 一一对应，DeepSeek/OpenAI 才会接受。
- 若已无工具轮次可删，则删除尾部最早一条普通消息。

说明：工具输出的长度截断由 tools/__init__.py 的 execute_tool 统一处理
（cfg.tool_output_limit），此处不做重复截断。
"""

from __future__ import annotations

from typing import Any

from .config import Config


class ContextManager:
    def __init__(self, cfg: Config, system_prompt: str, task: str):
        self.cfg = cfg
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task},
        ]
        # 尾部容量：至少留 2 条给 system+user
        self._tail_limit = max(2, cfg.max_messages - 2)

    def append(self, message: dict[str, Any]) -> None:
        """追加一条消息（不在此处裁剪；裁剪在轮次边界统一调用 trim）。"""
        self.messages.append(message)

    def to_list(self) -> list[dict[str, Any]]:
        return self.messages

    def trim(self) -> None:
        """在轮次边界调用：把尾部消息压缩到上限以内，保持协议合法。"""
        head = self.messages[:2]
        tail = self.messages[2:]
        while len(tail) > self._tail_limit:
            removed = False
            for i, m in enumerate(tail):
                if m["role"] == "assistant" and m.get("tool_calls"):
                    j = i + 1
                    while j < len(tail) and tail[j]["role"] == "tool":
                        j += 1
                    if j > i:  # 存在配套 tool 消息 → 整轮删除
                        del tail[i:j]
                        removed = True
                        break
            if not removed:
                # 没有可整轮删除的工具轮次，删掉尾部最早一条普通消息
                del tail[0]
        self.messages = head + tail

    def estimate_tokens(self) -> int:
        """粗略 token 估算（4 字符 ≈ 1 token），用于诊断/告警，非精确计费。"""
        total = 0
        for m in self.messages:
            total += 4  # 每条消息的基础开销
            content = m.get("content")
            if isinstance(content, str):
                total += len(content) // 4
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function", {})
                args = fn.get("arguments")
                if isinstance(args, str):
                    total += len(args) // 4
        return total
