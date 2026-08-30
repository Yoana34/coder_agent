"""DeepSeek（OpenAI 兼容）客户端。

用 requests 直接调用 /chat/completions，非流式。零 agent 框架依赖。
职责边界：
- 本模块只负责"发请求、收响应、做结构解析"（HTTP 层）。
- tool_calls 的 arguments 是 JSON 字符串，是否解析正确由 agent 层决定并做错误恢复。

错误处理：网络错误与 5xx/429 指数退避重试（1s/2s/4s），其他 4xx 立即失败。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

from .config import Config
from .errors import LLMError

_RETRYABLE_STATUS = {429, 500, 502, 503}
_MAX_RETRIES = 3


@dataclass
class ToolCall:
    id: str
    name: str
    arguments_raw: str  # JSON 字符串，由 agent 层解析


@dataclass
class ChatResult:
    content: str | None
    tool_calls: list[ToolCall] | None
    message: dict[str, Any]  # 完整的 assistant 消息（供历史回放，保证协议一致）


class DeepSeekClient:
    def __init__(self, cfg: Config, session: requests.Session | None = None):
        self.cfg = cfg
        self.session = session or requests.Session()
        self._sleep = time.sleep  # 测试可替换为 no-op

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> ChatResult:
        url = f"{self.cfg.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.cfg.model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        headers = {"Authorization": f"Bearer {self.cfg.api_key}"}
        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = self.session.post(url, json=payload, headers=headers, timeout=self.cfg.api_timeout)
            except requests.RequestException as e:
                last_error = LLMError(f"网络请求失败: {e}")
                if attempt < _MAX_RETRIES:
                    self._sleep(2**attempt)
                    continue
                raise last_error

            if resp.status_code == 200:
                return self._parse(resp.json())

            if resp.status_code in _RETRYABLE_STATUS and attempt < _MAX_RETRIES:
                last_error = LLMError(f"API 状态码 {resp.status_code}: {resp.text[:200]}")
                self._sleep(2**attempt)
                continue
            # 不可重试的 4xx（认证/参数错误）或重试耗尽
            raise LLMError(f"API 错误 {resp.status_code}: {resp.text[:300]}")

        raise LLMError(f"重试后仍失败: {last_error}")

    @staticmethod
    def _parse(data: dict[str, Any]) -> ChatResult:
        try:
            message: dict[str, Any] = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"响应格式异常（{e}）: {str(data)[:300]}")

        content = message.get("content")
        tool_calls: list[ToolCall] | None = None
        raw_tool_calls = message.get("tool_calls")
        if raw_tool_calls:
            tool_calls = []
            for tc in raw_tool_calls:
                fn = tc.get("function", {})
                tool_calls.append(
                    ToolCall(
                        id=tc.get("id", ""),
                        name=fn.get("name", ""),
                        arguments_raw=fn.get("arguments", "{}"),
                    )
                )
        return ChatResult(content=content, tool_calls=tool_calls, message=message)
