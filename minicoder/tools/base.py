"""Tool 抽象基类。

工具以"声明式"定义：每个工具提供 name / description / parameters(JSON Schema)，
序列化后即 OpenAI/DeepSeek 的 tools 参数。run() 返回字符串，由分发器统一截断与兜底。
"""

from __future__ import annotations

from typing import Any


class Tool:
    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}

    def run(self, args: dict[str, Any]) -> str:
        raise NotImplementedError

    def schema(self) -> dict[str, Any]:
        """OpenAI 兼容的 function 工具 schema。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
