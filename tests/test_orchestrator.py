"""Vérifie l'orchestrateur one-shot : parsing + garde OAuth (test déterministe)."""

import pytest
from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock

from intreepid.agent.orchestrator import run_agent
from intreepid.agent.profile import Profile


def _text_profile(on_result=None) -> Profile:
    return Profile(
        role="test",
        build_options=lambda model, thinking: ClaudeAgentOptions(),
        parse=lambda chunks: "\n".join(chunks).strip().upper(),
        on_result=on_result,
    )


async def test_run_agent_oneshot_returns_parsed(monkeypatch):
    async def fake_query(*, prompt, options):
        yield AssistantMessage(content=[TextBlock(text="result")], model="m")

    monkeypatch.setattr("intreepid.agent.orchestrator.query", fake_query)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    out = await run_agent(_text_profile(), "hi")
    assert out == "RESULT"


async def test_run_agent_calls_on_result_and_captures(monkeypatch, tmp_path):
    async def fake_query(*, prompt, options):
        yield AssistantMessage(content=[TextBlock(text="v")], model="m")

    monkeypatch.setattr("intreepid.agent.orchestrator.query", fake_query)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    seen: list = []
    prof = _text_profile(on_result=lambda scribe, result: seen.append(result))
    out = await run_agent(prof, "hi", trace_to=tmp_path / "ep.duckdb")
    assert out == "V"
    assert seen == ["V"]  # on_result reçoit le résultat parsé
    assert (tmp_path / "ep.duckdb").exists()  # capture greffier via run_agent


async def test_run_agent_refuses_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-x")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        await run_agent(_text_profile(), "hi")
