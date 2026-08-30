"""工具注册表与分发器。

- ALL_TOOLS / REGISTRY：全部工具的声明式集合
- tool_schemas()：供 LLM tools 参数使用
- execute_tool()：按名字分发执行；未知工具/异常统一转为错误字符串，绝不向模型层抛异常；
  输出统一截断，防止撑爆上下文。
"""

from __future__ import annotations

from typing import Any

from ..config import Config
from .base import Tool
from .read_file import ReadFileTool
from .run_command import RunCommandTool
from .write_file import WriteFileTool

ALL_TOOLS: list[Tool] = [ReadFileTool(), WriteFileTool(), RunCommandTool()]
REGISTRY: dict[str, Tool] = {t.name: t for t in ALL_TOOLS}


def tool_schemas() -> list[dict[str, Any]]:
    return [t.schema() for t in ALL_TOOLS]


def execute_tool(cfg: Config, name: str, args: dict[str, Any]) -> str:
    tool = REGISTRY.get(name)
    if tool is None:
        return f"[工具错误] 未知工具: {name}"
    try:
        result = tool.run(args)
    except Exception as e:  # noqa: BLE001 - 兜底：任何异常都转成字符串返回给模型
        result = f"[工具错误] {type(e).__name__}: {e}"
    return _truncate(result, cfg.tool_output_limit)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"
