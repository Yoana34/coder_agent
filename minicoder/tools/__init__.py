"""工具注册表与分发器。

- ALL_TOOLS / REGISTRY：全部工具的声明式集合
- tool_schemas()：供 LLM tools 参数使用
- execute_tool()：按名字分发执行；未知工具/异常统一转为错误字符串，绝不向模型层抛异常；
  输出统一截断，防止撑爆上下文。

工作区沙箱（workspace）：
- 传入 workspace 时，read_file / write_file 的 path 必须解析到工作区内，越界返回错误。
- run_command 默认 cwd=工作区；若显式给 cwd 也必须在工作区内。
- 这样 agent 只能读写自己的工作区，不会误改 minicoder 自身代码。
"""

from __future__ import annotations

import os
from typing import Any

from ..config import Config
from ..errors import ToolError
from .base import Tool
from .read_file import ReadFileTool
from .run_command import RunCommandTool
from .write_file import WriteFileTool

ALL_TOOLS: list[Tool] = [ReadFileTool(), WriteFileTool(), RunCommandTool()]
REGISTRY: dict[str, Tool] = {t.name: t for t in ALL_TOOLS}

# 需要把 path 解析到工作区内的工具
_PATH_TOOLS = {"read_file", "write_file"}
_CWD_TOOLS = {"run_command"}


def tool_schemas() -> list[dict[str, Any]]:
    return [t.schema() for t in ALL_TOOLS]


def execute_tool(cfg: Config, name: str, args: dict[str, Any], workspace: str | None = None) -> str:
    tool = REGISTRY.get(name)
    if tool is None:
        return f"[工具错误] 未知工具: {name}"
    try:
        if workspace:
            args = _apply_workspace(name, args, workspace)
        result = tool.run(args)
    except Exception as e:  # noqa: BLE001 - 兜底：任何异常都转成字符串返回给模型
        result = f"[工具错误] {type(e).__name__}: {e}"
    return _truncate(result, cfg.tool_output_limit)


def _apply_workspace(name: str, args: dict[str, Any], workspace: str) -> dict[str, Any]:
    args = dict(args)
    if name in _PATH_TOOLS and args.get("path"):
        args["path"] = _sandbox_path(workspace, str(args["path"]))
    elif name in _CWD_TOOLS:
        cwd = args.get("cwd")
        args["cwd"] = _sandbox_path(workspace, str(cwd)) if cwd else os.path.abspath(workspace)
    return args


def _sandbox_path(workspace: str, path: str) -> str:
    """把相对/绝对路径解析为工作区内的绝对路径；越界抛 ToolError。"""
    ws = os.path.abspath(workspace)
    target = os.path.abspath(os.path.join(ws, path))
    try:
        inside = os.path.commonpath([ws, target]) == ws
    except ValueError:  # 不同盘符（如 C: vs D:），必然越界
        inside = False
    if not inside:
        raise ToolError(f"路径越界: {path!r} 超出工作区 {ws}")
    return target


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"
