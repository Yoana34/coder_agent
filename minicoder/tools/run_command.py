"""run_command 工具：在本地 shell 执行命令，返回退出码与截断后的输出。"""

from __future__ import annotations

import subprocess
from typing import Any

from .base import Tool


class RunCommandTool(Tool):
    name = "run_command"
    description = (
        "在本地 shell 中执行一条命令并返回退出码、stdout 与 stderr。"
        "用于运行程序、跑测试、安装依赖、查看进程等。命令可能产生副作用，请谨慎。"
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "要执行的 shell 命令"},
            "timeout": {"type": "integer", "description": "超时秒数（默认 30，超时返回 124）", "default": 30},
            "cwd": {"type": "string", "description": "命令的工作目录（默认当前目录）"},
        },
        "required": ["command"],
    }

    def run(self, args: dict[str, Any]) -> str:
        command = args["command"]
        if not isinstance(command, str) or not command.strip():
            return "[run_command 错误] command 不能为空"
        try:
            timeout = int(args.get("timeout", 30))
        except (TypeError, ValueError):
            timeout = 30
        if timeout < 1:
            timeout = 1
        cwd = args.get("cwd") or None

        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=cwd,
            )
        except subprocess.TimeoutExpired:
            return (
                f"exit_code: 124\n"
                f"[run_command 超时] 命令在 {timeout}s 内未完成，已终止。"
            )
        except FileNotFoundError:
            return f"[run_command 错误] 工作目录不存在: {cwd}"
        except OSError as e:
            return f"[run_command 错误] {e}"

        parts = [f"exit_code: {proc.returncode}"]
        if proc.stdout and proc.stdout.strip():
            parts.append(f"[stdout]\n{proc.stdout.rstrip()}")
        if proc.stderr and proc.stderr.strip():
            parts.append(f"[stderr]\n{proc.stderr.rstrip()}")
        return "\n".join(parts)
