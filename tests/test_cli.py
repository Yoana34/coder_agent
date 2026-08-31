"""Step 6 验收：CLI 端到端（mock 模式）+ 退出码 + 多轮 REPL。"""

import os

import pytest

from minicoder.agent import Agent
from minicoder.cli import EXIT_OK, _repl, main
from minicoder.config import Config
from minicoder.mock_demo import FIXED_CONTENT
from minicoder.mock_llm import MockLLM

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


# ---------- 多轮对话 REPL ----------

def test_repl_multi_turn(tmp_path, capsys):
    """同一 agent 连续两轮：追问追加进历史，两次最终回复都输出。"""
    cfg = Config.from_env()
    script = [
        {"type": "final", "content": "第一轮完成。"},
        {"type": "final", "content": "第二轮完成。"},
    ]
    agent = Agent(cfg, MockLLM(script), echo=True, workspace=str(tmp_path))
    inputs = iter(["任务二", ""])
    rc = _repl(cfg, agent, mock=False, initial_task="任务一", get_input=lambda p: next(inputs))
    out = capsys.readouterr().out
    assert rc == EXIT_OK
    assert "第一轮完成。" in out and "第二轮完成。" in out
    # 两轮任务都进入了对话历史，上下文跨轮保留
    user_contents = [m["content"] for m in agent.messages if m["role"] == "user"]
    assert user_contents == ["任务一", "任务二"]


def test_repl_empty_first_task_exits(tmp_path):
    """未输入首个任务直接空行 → 退出，退出码 0。"""
    cfg = Config.from_env()
    agent = Agent(cfg, MockLLM([]), echo=False, workspace=str(tmp_path))
    rc = _repl(cfg, agent, mock=False, initial_task=None, get_input=lambda p: "")
    assert rc == EXIT_OK


def test_repl_exit_word_ends(tmp_path):
    """首轮完成后输入退出词 → 对话结束。"""
    cfg = Config.from_env()
    script = [{"type": "final", "content": "完成。"}]
    agent = Agent(cfg, MockLLM(script), echo=False, workspace=str(tmp_path))
    rc = _repl(cfg, agent, mock=False, initial_task="任务", get_input=lambda p: "退出")
    assert rc == EXIT_OK


def test_repl_mock_single_turn(tmp_path):
    """mock 模式只演示一轮后自动退出，不再询问输入。"""
    cfg = Config.from_env()
    script = [{"type": "final", "content": "演示完成。"}]
    agent = Agent(cfg, MockLLM(script), echo=False, workspace=str(tmp_path))

    def should_not_prompt(prompt):
        raise AssertionError("mock 模式不应再询问输入")

    rc = _repl(cfg, agent, mock=True, initial_task="演示任务", get_input=should_not_prompt)
    assert rc == EXIT_OK
