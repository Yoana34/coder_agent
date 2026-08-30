"""read_file 工具：带行号读取文本文件。失败返回错误字符串而非抛异常。"""

from __future__ import annotations

from typing import Any

from .base import Tool


class ReadFileTool(Tool):
    name = "read_file"
    description = "读取指定文本文件的指定行区间（带行号）。用于查看源码、配置、日志等。"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "offset": {"type": "integer", "description": "起始行号（0 起，默认 0）", "default": 0},
            "limit": {"type": "integer", "description": "最多读取的行数（默认 2000）", "default": 2000},
        },
        "required": ["path"],
    }

    def run(self, args: dict[str, Any]) -> str:
        path = args["path"]
        try:
            offset = int(args.get("offset", 0))
        except (TypeError, ValueError):
            offset = 0
        try:
            limit = int(args.get("limit", 2000))
        except (TypeError, ValueError):
            limit = 2000
        if offset < 0:
            offset = 0
        if limit < 1:
            limit = 1

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return f"[read_file 错误] 文件不存在: {path}"
        except IsADirectoryError:
            return f"[read_file 错误] 路径是目录而非文件: {path}"
        except OSError as e:
            return f"[read_file 错误] {e}"

        end = min(offset + limit, len(lines))
        if offset >= len(lines):
            return f"[read_file] 文件 {path} 共 {len(lines)} 行，offset={offset} 已超出范围"
        chosen = lines[offset:end]
        body = "\n".join(f"{i + 1}: {ln.rstrip()}" for i, ln in enumerate(chosen, start=offset))
        header = f"<file: {path}> (lines {offset + 1}-{end} of {len(lines)})"
        return header + "\n" + body
