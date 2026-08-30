"""Step 3 验收：LLM 客户端与 mock 的单元测试。"""

import pytest

from minicoder.config import Config
from minicoder.errors import LLMError
from minicoder.llm import ChatResult, DeepSeekClient, ToolCall
from minicoder.mock_llm import MockLLM


@pytest.fixture
def cfg() -> Config:
    return Config.from_env(
        api_key="test-key",
        base_url="https://example.com",
        model="test-model",
        api_timeout=10,
    )


class FakeResp:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text or str(json_data)

    def json(self):
        return self._json


def tool_calls_payload():
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "read_file", "arguments": '{"path": "a.py"}'},
                        }
                    ],
                }
            }
        ]
    }


def text_payload(text="搞定了"):
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


# ---------- DeepSeekClient ----------

def test_parse_tool_calls(cfg):
    client = DeepSeekClient(cfg, session=_make_session(lambda *a, **k: FakeResp(200, tool_calls_payload())))
    client._sleep = lambda _s: None
    result = client.chat(messages=[{"role": "user", "content": "hi"}], tools=[])
    assert isinstance(result, ChatResult)
    assert result.content is None
    assert result.tool_calls is not None and len(result.tool_calls) == 1
    tc = result.tool_calls[0]
    assert tc.id == "call_1" and tc.name == "read_file" and tc.arguments_raw == '{"path": "a.py"}'
    # message 保留完整 assistant 消息供历史回放
    assert result.message["role"] == "assistant" and result.message["tool_calls"][0]["id"] == "call_1"


def test_parse_text(cfg):
    client = DeepSeekClient(cfg, session=_make_session(lambda *a, **k: FakeResp(200, text_payload())))
    client._sleep = lambda _s: None
    result = client.chat(messages=[])
    assert result.content == "搞定了" and result.tool_calls is None


def test_auth_error_fails_fast(cfg):
    calls = {"n": 0}

    def fake_post(*a, **k):
        calls["n"] += 1
        return FakeResp(401, {}, "unauthorized")

    client = DeepSeekClient(cfg, session=_make_session(fake_post))
    with pytest.raises(LLMError, match="401"):
        client.chat(messages=[])
    assert calls["n"] == 1  # 不可重试，只发一次


def test_retry_then_success(cfg):
    seq = [FakeResp(500, {}, "boom"), FakeResp(200, text_payload())]
    client = DeepSeekClient(cfg, session=_make_session(_sequential(seq)))
    client._sleep = lambda _s: None
    result = client.chat(messages=[])
    assert result.content == "搞定了"


def test_network_error_retries_then_raises(cfg):
    import requests

    def always_raise(*a, **k):
        raise requests.ConnectionError("down")

    client = DeepSeekClient(cfg, session=_make_session(always_raise))
    client._sleep = lambda _s: None
    with pytest.raises(LLMError, match="网络请求失败"):
        client.chat(messages=[])


# ---------- MockLLM ----------

def test_mock_sequence(cfg):
    mock = MockLLM(
        [
            {"type": "tools", "tool_calls": [{"name": "read_file", "arguments": {"path": "a.py"}}]},
            {"type": "final", "content": "完成"},
        ]
    )
    r1 = mock.chat(messages=[])
    assert r1.tool_calls and r1.tool_calls[0].name == "read_file"
    assert r1.tool_calls[0].arguments_raw == '{"path": "a.py"}'
    r2 = mock.chat(messages=[])
    assert r2.content == "完成" and r2.tool_calls is None


def test_mock_exhausted_raises():
    mock = MockLLM([{"type": "final", "content": "ok"}])
    mock.chat(messages=[])
    with pytest.raises(LLMError, match="脚本已用完"):
        mock.chat(messages=[])


# ---------- helpers ----------

def _make_session(post_impl):
    class FakeSession:
        def __init__(self):
            self.post = post_impl

    return FakeSession()


def _sequential(responses):
    it = iter(responses)

    def fake_post(*a, **k):
        return next(it)

    return fake_post
