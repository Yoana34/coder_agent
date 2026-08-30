"""Step 6 验收：CLI 端到端（mock 模式）+ 退出码。"""

import os

import pytest

from minicoder.cli import main
from minicoder.mock_demo import FIXED_CONTENT

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_missing_key_exit_config(monkeypatch, capsys):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    rc = main(["任意任务"])
    assert rc == 2
    assert "DEEPSEEK_API_KEY" in capsys.readouterr().out


def test_mock_mode_demo_fixes_file(tmp_path, monkeypatch, capsys):
    """mock 模式在临时目录跑完整闭环：读→修→跑→总结，文件被真实修复。"""
    # 从仓库复制 demo 场景到临时目录
    src_demo = os.path.join(_REPO_ROOT, "demo")
    dst_demo = tmp_path / "demo"
    dst_demo.mkdir()
    (dst_demo / "buggy_wordcount.py").write_text(
        open(os.path.join(src_demo, "buggy_wordcount.py"), encoding="utf-8").read(),
        encoding="utf-8",
    )
    (dst_demo / "sample.txt").write_text(
        open(os.path.join(src_demo, "sample.txt"), encoding="utf-8").read(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    rc = main(["--mock", "修复单词统计 bug"])
    out = capsys.readouterr().out
    assert rc == 0
    # 修复后文件内容与 mock 脚本一致
    fixed = (dst_demo / "buggy_wordcount.py").read_text(encoding="utf-8")
    assert fixed == FIXED_CONTENT
    assert "11" in out  # 运行验证输出正确计数
    assert "完成" in out
