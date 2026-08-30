"""Step 5 验收：上下文管理的单元测试。"""

import pytest

from minicoder.config import Config
from minicoder.context import ContextManager


@pytest.fixture
def cfg() -> Config:
    return Config.from_env(max_messages=6)


def _tool_round(cid, path="a.py"):
    """构造一个完整工具轮次的两条消息。"""
    assistant = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": cid, "type": "function", "function": {"name": "read_file", "arguments": '{"path": "%s"}' % path}}
        ],
    }
    tool = {"role": "tool", "tool_call_id": cid, "content": f"<file: {path}> x"}
    return assistant, tool


def _assert_protocol_valid(messages):
    """每条 tool 消息必须有匹配的 assistant.tool_calls。"""
    known_ids = set()
    for m in messages:
        for tc in m.get("tool_calls") or []:
            known_ids.add(tc["id"])
    for m in messages:
        if m["role"] == "tool":
            assert m["tool_call_id"] in known_ids


def test_system_and_user_kept(cfg):
    ctx = ContextManager(cfg, "SYSTEM", "TASK")
    for _ in range(20):
        ctx.append({"role": "assistant", "content": "思考..."})
    ctx.trim()
    assert ctx.messages[0] == {"role": "system", "content": "SYSTEM"}
    assert ctx.messages[1] == {"role": "user", "content": "TASK"}
    assert len(ctx.messages) <= cfg.max_messages


def test_trim_removes_whole_tool_rounds(cfg):
    ctx = ContextManager(cfg, "SYSTEM", "TASK")
    # 追加 4 轮完整工具轮次（每轮 2 条 → 尾部 8 条，超出上限 6）
    for i in range(4):
        a, t = _tool_round(f"call_{i}")
        ctx.append(a)
        ctx.append(t)
    ctx.trim()
    assert len(ctx.messages) <= cfg.max_messages
    # system + user 保留
    assert ctx.messages[0]["role"] == "system"
    assert ctx.messages[1]["role"] == "user"
    # 协议仍合法（无孤儿 tool 消息）
    _assert_protocol_valid(ctx.messages)
    # 最老的 call_0 轮次应被整轮删除（assistant 与 tool 一起）
    all_text = str(ctx.messages)
    assert "call_0" not in all_text


def test_trim_no_orphan_even_when_only_rounds(cfg):
    """即使全部都是工具轮次，删除也成对进行。"""
    small = Config.from_env(max_messages=4)
    ctx = ContextManager(small, "SYSTEM", "TASK")
    for i in range(6):
        a, t = _tool_round(f"call_{i}")
        ctx.append(a)
        ctx.append(t)
    ctx.trim()
    assert len(ctx.messages) <= 4
    _assert_protocol_valid(ctx.messages)


def test_estimate_tokens(cfg):
    ctx = ContextManager(cfg, "SYSTEM", "TASK")
    a, t = _tool_round("call_x")
    ctx.append(a)
    ctx.append(t)
    assert ctx.estimate_tokens() > 0
