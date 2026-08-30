"""write_file 工具：创建或覆盖写入文件（自动建父目录）。"""

from __future__ import annotations

import os
from typing import Any

from .base import Tool


class WriteFileTool(Tool):
    name = "write_file"
    description = "创建或覆盖写入一个文本文件（自动创建父目录）。用于写代码、配置、数据等。"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "content": {"type": "string", "description": "写入的完整文件内容"},
        },
        "required": ["path", "content"],
    }

    def run(self, args: dict[str, Any]) -> str:
        path = args["path"]
        content = args.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        try:
            parent = os.path.dirname(os.path.abspath(path))
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
        except OSError as e:
            return f"[write_file 错误] {e}"
        return f"已写入 {len(content)} 字符到 {path}"
