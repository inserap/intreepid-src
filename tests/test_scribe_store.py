"""Vérifie la persistance DuckDB du greffier : round-trip, scellement, immuabilité."""

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from intreepid.agent.verdict import Observation
from intreepid.scribe.store import Scribe, load


def _session(db, sid="s1"):
    with Scribe(db, sid, "q?", "opus") as sc:
        sc.record(
            AssistantMessage(
                content=[
                    ThinkingBlock(thinking="hyp", signature="x"),
                    ToolUseBlock(id="t1", name="n", input={}),
                ],
                model="opus",
            )
        )
        sc.record(
            UserMessage(content=[ToolResultBlock(tool_use_id="t1", content="agrégat")])
        )
        sc.record_verdict(
            [Observation(claim="c", statut="fait", note="n", confiance="haute")]
        )


def test_roundtrip_closed(tmp_path):
    db = tmp_path / "ep.duckdb"
    _session(db)
    tr = load(db, "s1")
    assert tr.status == "closed"
    kinds = [n.kind for n in tr.nodes]
    assert kinds[0] == "session_root"
    for k in ("thinking", "tool_call", "tool_result", "observation"):
        assert k in kinds
    call = next(n for n in tr.nodes if n.kind == "tool_call")
    res = next(n for n in tr.nodes if n.kind == "tool_result")
    assert res.parent_id == call.id


def test_store_file_is_created_and_distinct(tmp_path):
    db = tmp_path / "ep.duckdb"
    _session(db)
    assert db.exists()  # P3 : le greffier écrit dans SON fichier, pas dans une source


def test_interrupt_seals_aborted_and_keeps_nodes(tmp_path):
    db = tmp_path / "ep.duckdb"
    with pytest.raises(RuntimeError):
        with Scribe(db, "s1", "q?", "opus") as sc:
            sc.record(
                AssistantMessage(
                    content=[ToolUseBlock(id="t1", name="n", input={})], model="opus"
                )
            )
            raise RuntimeError("boom")
    tr = load(db, "s1")
    assert tr.status == "aborted"
    assert "boom" in tr.meta.get("aborted_reason", "")
    assert any(
        n.kind == "tool_call" for n in tr.nodes
    )  # nœud pré-interruption conservé


def test_sealed_session_is_immutable(tmp_path):
    db = tmp_path / "ep.duckdb"
    _session(db)
    with pytest.raises(ValueError):
        with Scribe(db, "s1", "q?", "opus"):  # même session_id déjà scellée
            pass
