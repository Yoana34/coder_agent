"""Step 6 验收：CLI 端到端（mock 模式）+ 退出码。"""

import os

import pytest

from minicoder.cli import main
from minicoder.mock_demo import FIXED_CONTENT

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_missing_key_exit_config(monkeypatch, capsys):
    # 设为空串而非 delenv：load_dotenv 只注入不存在的 key，
    # delenv 后 .env 会把 key 加回来导致走真实 API。空串则直接触发校验错误。
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    rc = main(["任意任务"])
    assert rc == 2
    assert "DEEPSEEK_API_KEY" in capsys.readouterr().out


def test_mock_mode_demo_fixes_file(tmp_path, monkeypatch, capsys):
    """mock 模式在临时目录跑完整闭环：读→修→跑→总结，文件在工作区被真实修复。"""
    monkeypatch.chdir(tmp_path)

    rc = main(["--mock", "修复单词统计 bug"])
    out = capsys.readouterr().out
    assert rc == 0
    # 修复后的文件位于默认工作区 <cwd>/workspace，内容与 mock 脚本一致
    fixed = (tmp_path / "workspace" / "buggy_wordcount.py").read_text(encoding="utf-8")
    assert fixed == FIXED_CONTENT
    assert "11" in out  # 运行验证输出正确计数
    assert "完成" in out
