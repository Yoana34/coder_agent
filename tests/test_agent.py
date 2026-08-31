"""Step 4 验收：Agent 主循环的单元测试（用 mock LLM，离线确定性）。"""

import pytest

from minicoder.agent import Agent
from minicoder.config import Config
from minicoder.errors import AgentLimitExceeded
from minicoder.mock_llm import MockLLM


@pytest.fixture
def cfg() -> Config:
    return Config.from_env(max_iterations=15, tool_output_limit=200)


def make_agent(cfg, mock):
    return Agent(cfg, mock, echo=False)


# ---------- 场景 A：任务完成（读→写→跑→最终回复） ----------

def test_task_completes(cfg, tmp_path):
    target = tmp_path / "result.txt"
    script = [
        {
            "type": "tools",
            "tool_calls": [{"name": "write_file", "arguments": {"path": str(target), "content": "hello agent\n"}}],
        },
        {
            "type": "tools",
            "tool_calls": [{"name": "run_command", "arguments": {"command": 'python -c "print(1+1)"', "timeout": 10}}],
        },
        {"type": "final", "content": "任务完成，文件已写入。"},
    ]
    agent = make_agent(cfg, MockLLM(script))
    final = agent.run("写入一个文件")
    assert final == "任务完成，文件已写入。"
    # 文件确实被工具执行写入
    assert target.read_text(encoding="utf-8") == "hello agent\n"
    # 历史协议：system+user 开头，assistant(tool_calls) 后有对应的 tool 消息
    roles = [m["role"] for m in agent.messages]
    assert roles[0] == "system" and roles[1] == "user"
    assert "assistant" in roles and "tool" in roles
    # 每个 assistant.tool_calls 都有匹配的 tool_call_id 工具结果
    for m in agent.messages:
        if m["role"] == "tool":
            assert m["tool_call_id"]


# ---------- 场景 B：永不收敛 → 达最大轮数 ----------

def test_max_iterations(cfg):
    script = [
        {"type": "tools", "tool_calls": [{"name": "read_file", "arguments": {"path": "x"}}]}
        for _ in range(3)
    ]  # 全是工具调用，永不结束
    small_cfg = Config.from_env(max_iterations=3)
    agent = make_agent(small_cfg, MockLLM(script))
    with pytest.raises(AgentLimitExceeded, match="最大迭代轮数"):
        agent.run("一直调用工具")


# ---------- 场景 C：坏 JSON 参数 → 回传错误 → 模型重发正确参数 → 完成 ----------

def test_bad_json_args_recovery(cfg, tmp_path):
    target = tmp_path / "a.txt"
    script = [
        {
            "type": "tools",
            "tool_calls": [{"name": "read_file", "arguments": '{"path": "unterminated'}],  # 坏 JSON
        },
        {
            "type": "tools",
            "tool_calls": [{"name": "write_file", "arguments": {"path": str(target), "content": "ok"}}],
        },
        {"type": "final", "content": "修正后完成"},
    ]
    agent = make_agent(cfg, MockLLM(script))
    final = agent.run("测试")
    assert final == "修正后完成"
    # 坏参数未执行工具，且向模型回传了错误；之后正常执行 write_file
    tool_msgs = [m for m in agent.messages if m["role"] == "tool"]
    assert len(tool_msgs) == 2
    assert "参数解析错误" in tool_msgs[0]["content"]
    assert target.read_text(encoding="utf-8") == "ok"


# ---------- 场景 E：多轮对话 —— 上下文跨轮保留 ----------

def test_multi_turn_preserves_context(cfg):
    """同一 agent 连续 run 两次：追问追加进已有历史，之前的工作结果仍可见。"""
    script = [
        {"type": "final", "content": "第一轮完成。"},
        {"type": "final", "content": "第二轮完成，已基于之前的上下文作答。"},
    ]
    agent = make_agent(cfg, MockLLM(script))

    final1 = agent.run("第一个任务")
    assert final1 == "第一轮完成。"
    # 第一轮的最终回复已写入历史
    assert agent.messages[1] == {"role": "user", "content": "第一个任务"}
    assert any(m["role"] == "assistant" and m["content"] == "第一轮完成。" for m in agent.messages)

    final2 = agent.run("继续：把结果改成大写")
    assert final2 == "第二轮完成，已基于之前的上下文作答。"
    # 追问在尾部，初始任务仍常驻，历史被完整保留（无重置）
    roles = [m["role"] for m in agent.messages]
    assert roles[1] == "user" and agent.messages[1]["content"] == "第一个任务"
    assert roles[-1] == "assistant"
    assert agent.messages[-2] == {"role": "user", "content": "继续：把结果改成大写"}
    # 两个任务都在历史里
    user_contents = [m["content"] for m in agent.messages if m["role"] == "user"]
    assert "第一个任务" in user_contents and "继续：把结果改成大写" in user_contents


# ---------- 场景 D：Ctrl+C 干净中断（异常上抛，由 CLI 处理） ----------

class KillLLM:
    """模拟模型调用中途被 Ctrl+C 打断。"""

    def chat(self, messages, tools=None):
        raise KeyboardInterrupt


def test_ctrl_c_interrupts(cfg):
    agent = make_agent(cfg, KillLLM())
    with pytest.raises(KeyboardInterrupt):
        agent.run("会被中断")
