"""Vérifie le câblage du greffier dans le runner (query() mocké, sans réseau).

Non marqué `agent` : monkeypatch `query` par un flux factice → déterministe.
"""

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from intreepid.agent import runner
from intreepid.scribe.store import load


async def _fake_query(*, prompt, options):
    yield AssistantMessage(
        content=[
            ToolUseBlock(
                id="t1", name="mcp__intreepid__profile_stats", input={"table": "z"}
            )
        ],
        model="test",
    )
    yield UserMessage(content=[ToolResultBlock(tool_use_id="t1", content="agrégat")])
    yield AssistantMessage(
        content=[TextBlock(text='[{"claim": "c", "statut": "fait"}]')], model="test"
    )


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(runner, "query", _fake_query)


async def test_build_options_thinking_toggle():
    assert runner._build_options().thinking is None
    assert runner._build_options(thinking=True).thinking == {
        "type": "adaptive",
        "display": "summarized",
    }


async def test_no_capture_when_trace_to_none(tmp_path):
    obs = await runner.run_analysis("q?", model=None, trace_to=None)
    assert [o.statut for o in obs] == ["fait"]
    assert not list(tmp_path.iterdir())  # aucun store écrit


async def test_capture_writes_tree(tmp_path):
    db = tmp_path / "ep.duckdb"
    obs = await runner.run_analysis("q?", model=None, trace_to=db)
    assert [o.claim for o in obs] == ["c"]  # verdict inchangé (non-régression)
    # une seule session écrite → la retrouver
    import duckdb

    row = (
        duckdb.connect(str(db), read_only=True)
        .execute("SELECT session_id FROM sessions")
        .fetchone()
    )
    assert row is not None
    sid = row[0]
    tr = load(db, sid)
    assert tr.status == "closed"
    assert any(n.kind == "tool_call" for n in tr.nodes)
    assert any(n.kind == "observation" for n in tr.nodes)
