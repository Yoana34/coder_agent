"""Step 2 验收：工具框架与三个工具的单元测试（含工作区沙箱）。"""

import os

import pytest

from minicoder.config import Config
from minicoder.tools import (
    ALL_TOOLS,
    execute_tool,
    tool_schemas,
)
from minicoder.tools.read_file import ReadFileTool
from minicoder.tools.run_command import RunCommandTool
from minicoder.tools.write_file import WriteFileTool


@pytest.fixture
def cfg() -> Config:
    return Config.from_env(tool_output_limit=200)


# ---------- read_file ----------

def test_read_file_ok(tmp_path):
    p = tmp_path / "hello.txt"
    p.write_text("line1\nline2\nline3\n", encoding="utf-8")
    out = ReadFileTool().run({"path": str(p)})
    assert "line1" in out and "1: line1" in out
    assert "lines 1-3 of 3" in out


def test_read_file_missing(tmp_path):
    out = ReadFileTool().run({"path": str(tmp_path / "nope.txt")})
    assert "文件不存在" in out


def test_read_file_directory(tmp_path):
    out = ReadFileTool().run({"path": str(tmp_path)})
    assert "目录" in out or "错误" in out


def test_read_file_offset_limit(tmp_path):
    p = tmp_path / "nums.txt"
    p.write_text("\n".join(f"line{i}" for i in range(10)), encoding="utf-8")
    out = ReadFileTool().run({"path": str(p), "offset": 3, "limit": 2})
    assert "line3" in out and "line4" in out and "line5" not in out


# ---------- write_file ----------

def test_write_file_overwrite_and_parent_dirs(tmp_path):
    p = tmp_path / "a" / "b" / "out.py"
    out = WriteFileTool().run({"path": str(p), "content": "x = 1\n"})
    assert "已写入" in out
    assert p.read_text(encoding="utf-8") == "x = 1\n"
    # 覆盖写
    WriteFileTool().run({"path": str(p), "content": "y = 2\n"})
    assert p.read_text(encoding="utf-8") == "y = 2\n"


# ---------- run_command ----------

def test_run_command_success():
    out = RunCommandTool().run({"command": "echo hello-minicoder", "timeout": 10})
    assert "exit_code: 0" in out
    assert "hello-minicoder" in out


def test_run_command_failure_exit_code():
    # 注意：Windows cmd 不识别单引号，python -c 参数需用双引号包裹
    out = RunCommandTool().run({"command": 'python -c "import sys; sys.exit(3)"', "timeout": 10})
    assert "exit_code: 3" in out


def test_run_command_timeout():
    out = RunCommandTool().run(
        {"command": 'python -c "import time; time.sleep(5)"', "timeout": 1}
    )
    assert "124" in out and "超时" in out


# ---------- registry / dispatcher ----------

def test_schemas_count_and_structure():
    schemas = tool_schemas()
    assert len(schemas) == 3
    names = {s["function"]["name"] for s in schemas}
    assert names == {"read_file", "write_file", "run_command"}
    assert schemas[0]["function"]["parameters"]["type"] == "object"


def test_unknown_tool_returns_error_string(cfg):
    out = execute_tool(cfg, "no_such_tool", {})
    assert "未知工具" in out


def test_truncation(tmp_path):
    small_cfg = Config.from_env(tool_output_limit=50)
    p = tmp_path / "long.txt"
    p.write_text("x" * 500, encoding="utf-8")
    out = execute_tool(small_cfg, "read_file", {"path": str(p)})
    # 截断后应远短于原始内容，且带标记
    assert len(out) < 150
    assert "truncated" in out


def test_tool_run_raises_is_caught(cfg, tmp_path):
    # read_file 传不可序列化参数路径（None）应被分发器兜底成错误字符串
    out = execute_tool(cfg, "read_file", {"path": None})
    assert "[工具错误]" in out or "[read_file 错误]" in out


# ---------- 工作区沙箱（workspace） ----------

def test_sandbox_write_inside_workspace(cfg, tmp_path):
    ws = tmp_path / "ws"
    out = execute_tool(cfg, "write_file", {"path": "out.py", "content": "x = 1\n"}, workspace=str(ws))
    assert "已写入" in out
    assert (ws / "out.py").read_text(encoding="utf-8") == "x = 1\n"
    # 原目录不应被写入
    assert not (tmp_path / "out.py").exists()


def test_sandbox_read_absolute_path_inside_ok(cfg, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "a.txt").write_text("hello\n", encoding="utf-8")
    out = execute_tool(cfg, "read_file", {"path": "a.txt"}, workspace=str(ws))
    assert "hello" in out


def test_sandbox_blocks_relative_escape(cfg, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    out = execute_tool(cfg, "read_file", {"path": "../secret.txt"}, workspace=str(ws))
    assert "越界" in out


def test_sandbox_blocks_absolute_escape(cfg, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("top secret\n", encoding="utf-8")
    out = execute_tool(cfg, "read_file", {"path": str(outside)}, workspace=str(ws))
    assert "越界" in out


def test_sandbox_blocks_write_escape(cfg, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    out = execute_tool(
        cfg, "write_file", {"path": "../evil.py", "content": "x = 1\n"}, workspace=str(ws)
    )
    assert "越界" in out
    assert not (tmp_path / "evil.py").exists()


def test_sandbox_run_command_defaults_to_workspace(cfg, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    out = execute_tool(
        cfg,
        "run_command",
        {"command": 'python -c "import os; print(os.getcwd())"', "timeout": 15},
        workspace=str(ws),
    )
    assert os.path.abspath(str(ws)) in out


def test_sandbox_run_command_cwd_escape_blocked(cfg, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    out = execute_tool(
        cfg,
        "run_command",
        {"command": "echo hi", "cwd": str(tmp_path), "timeout": 15},
        workspace=str(ws),
    )
    assert "越界" in out


def test_no_workspace_means_no_restriction(cfg, tmp_path):
    # workspace=None（测试/默认）时不沙箱，行为与之前一致
    out = execute_tool(cfg, "read_file", {"path": "demo/does_not_matter"}, workspace=None)
    assert isinstance(out, str)
