"""Offline tests for the provider-neutral LLM layer (HTTP is mocked)."""
import json

import httpx
import pytest

from app import llm
from app.config import Settings, settings

GOOD = {"risk_score": 0.9, "scam_type": "toll", "red_flags": [{"flag": "lookalike", "evidence": "x"}],
        "recommended_action": "Delete it.", "plain_language_summary": "Fake toll bill."}


def test_parse_verdict_handles_fences_chatter_and_loose_types():
    raw = 'Sure! ```json\n' + json.dumps({**GOOD, "risk_score": "1.4", "red_flags": ["urgency"]}) + "\n```"
    v = llm.parse_verdict(raw)
    assert v.risk_score == 1.0  # string coerced, then clamped
    assert v.red_flags[0].flag == "urgency"


def test_parse_verdict_rejects_garbage():
    assert llm.parse_verdict("I can't help with that.") is None
    assert llm.parse_verdict('{"risk_score": "high"}') is None


def test_old_claude_env_names_still_work(monkeypatch):
    monkeypatch.setenv("CLAUDE_MODEL", "claude-haiku-4-5")
    monkeypatch.setenv("CLAUDE_EFFORT", "")
    s = Settings(_env_file=None)
    assert s.model == "claude-haiku-4-5" and s.llm_effort == ""


@pytest.fixture
def openai_server(monkeypatch):
    """Fake OpenAI-compatible server that rejects JSON mode, like some local servers."""
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        calls.append((str(req.url), req.headers.get("authorization"), body))
        if "response_format" in body:
            return httpx.Response(400, json={"error": "response_format not supported"})
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(GOOD)}}]})

    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_model", "llama3.1")
    monkeypatch.setattr(settings, "llm_base_url", "http://localhost:11434/v1/")
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(llm, "_http", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    return calls


@pytest.mark.asyncio
async def test_openai_compatible_judge_retries_without_json_mode(openai_server):
    v = await llm.judge("Pay your toll at ezpass-tollpay.com", [])
    assert v.risk_score == 0.9
    assert [c[0] for c in openai_server] == ["http://localhost:11434/v1/chat/completions"] * 2
    assert openai_server[1][1] is None  # no key, no auth header
    assert openai_server[1][2]["model"] == "llama3.1"


@pytest.mark.asyncio
async def test_openai_compatible_failure_falls_back(monkeypatch, openai_server):
    monkeypatch.setattr(llm, "_http", lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(500, text="boom"))))
    assert await llm.judge("hi", []) is None
