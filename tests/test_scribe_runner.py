"""Vérifie le câblage du greffier dans le runner (query() mocké, sans réseau).

Non marqué `agent` : monkeypatch `query` par un flux factice → déterministe.
"""

import duckdb
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
    captured_options: list = []

    async def _fake_query_capture(*, prompt, options):
        captured_options.append(options)
        yield AssistantMessage(
            content=[TextBlock(text='[{"claim": "c", "statut": "fait"}]')], model="test"
        )

    runner.query = _fake_query_capture  # type: ignore[assignment]
    obs = await runner.run_analysis("q?", model=None, trace_to=None)
    assert [o.statut for o in obs] == ["fait"]
    assert not list(tmp_path.iterdir())  # aucun store écrit
    assert len(captured_options) == 1
    assert captured_options[0].thinking is None


async def test_capture_writes_tree(tmp_path):
    captured_options: list = []

    async def _fake_query_capture(*, prompt, options):
        captured_options.append(options)
        yield AssistantMessage(
            content=[
                ToolUseBlock(
                    id="t1", name="mcp__intreepid__profile_stats", input={"table": "z"}
                )
            ],
            model="test",
        )
        yield UserMessage(
            content=[ToolResultBlock(tool_use_id="t1", content="agrégat")]
        )
        yield AssistantMessage(
            content=[TextBlock(text='[{"claim": "c", "statut": "fait"}]')], model="test"
        )

    runner.query = _fake_query_capture  # type: ignore[assignment]
    db = tmp_path / "ep.duckdb"
    obs = await runner.run_analysis("q?", model=None, trace_to=db)
    assert [o.claim for o in obs] == ["c"]  # verdict inchangé (non-régression)
    # une seule session écrite → la retrouver
    con = duckdb.connect(str(db), read_only=True)
    try:
        row = con.execute("SELECT session_id FROM sessions").fetchone()
    finally:
        con.close()
    assert row is not None
    sid = row[0]
    tr = load(db, sid)
    assert tr.status == "closed"
    assert any(n.kind == "tool_call" for n in tr.nodes)
    assert any(n.kind == "observation" for n in tr.nodes)
    assert len(captured_options) == 1
    assert captured_options[0].thinking == {"type": "adaptive", "display": "summarized"}


async def test_scribe_record_failure_does_not_interrupt_analyst(tmp_path, monkeypatch):
    """Une panne du scribe.record ne doit pas interrompre l'analyste."""
    from intreepid.scribe import store as store_mod

    monkeypatch.setattr(
        store_mod.Scribe,
        "record",
        lambda self, msg: (_ for _ in ()).throw(RuntimeError("boom scribe")),
    )  # type: ignore[assignment]

    db = tmp_path / "ep.duckdb"
    obs = await runner.run_analysis("q?", model=None, trace_to=db)
    # verdict still returned
    assert [o.statut for o in obs] == ["fait"]
    # session sealed (closed)
    con = duckdb.connect(str(db), read_only=True)
    try:
        row = con.execute("SELECT status FROM sessions").fetchone()
    finally:
        con.close()
    assert row is not None
    assert row[0] == "closed"


async def test_scribe_open_failure_disables_capture(tmp_path, monkeypatch):
    """Si Scribe.__enter__ échoue, l'analyste tourne sans capture."""
    from intreepid.scribe import store as store_mod

    def _boom_enter(self):
        raise RuntimeError("boom open")

    monkeypatch.setattr(store_mod.Scribe, "__enter__", _boom_enter)

    db = tmp_path / "ep.duckdb"
    obs = await runner.run_analysis("q?", model=None, trace_to=db)
    # verdict returned normally
    assert [o.statut for o in obs] == ["fait"]
    # no store file written (or if the file was created before the error, no sessions)
    assert not db.exists()


async def test_analyst_exception_seals_aborted(tmp_path, monkeypatch):
    """Une exception de l'analyste scelle la session en 'aborted'."""
    from claude_agent_sdk import AssistantMessage, ToolUseBlock

    async def _failing_query(*, prompt, options):
        yield AssistantMessage(
            content=[ToolUseBlock(id="t1", name="mcp__x__profile", input={})],
            model="test",
        )
        raise RuntimeError("boom analyste")

    monkeypatch.setattr(runner, "query", _failing_query)

    db = tmp_path / "ep.duckdb"
    with pytest.raises(RuntimeError, match="boom analyste"):
        await runner.run_analysis("q?", model=None, trace_to=db)

    # find the session id
    con = duckdb.connect(str(db), read_only=True)
    try:
        row = con.execute("SELECT session_id FROM sessions").fetchone()
    finally:
        con.close()
    assert row is not None
    sid = str(row[0])

    tr = load(db, sid)
    assert tr.status == "aborted"
    assert "boom analyste" in tr.meta.get("aborted_reason", "")
    assert any(n.kind == "tool_call" for n in tr.nodes)
