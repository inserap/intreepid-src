"""Vérifie la persistance DuckDB du greffier : round-trip, scellement, immuabilité."""

from datetime import datetime, timedelta, timezone

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

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
        sc.record_nodes(
            [
                (
                    "observation",
                    {"claim": "c", "note": "n"},
                    {"statut": "fait", "confiance": "haute", "nature": None},
                )
            ]
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


def test_aborted_session_cannot_be_reopened(tmp_path):
    """Une session abortée (status='aborted') refuse tout ré-ouverture."""
    import pytest

    db = tmp_path / "ep.duckdb"
    with pytest.raises(RuntimeError):
        with Scribe(db, "s1", "q?", "opus") as sc:
            sc.record(
                AssistantMessage(
                    content=[ToolUseBlock(id="t1", name="n", input={})], model="opus"
                )
            )
            raise RuntimeError("boom abort")
    # session is now aborted — trying to reopen must raise ValueError
    with pytest.raises(ValueError, match="immuable"):
        with Scribe(db, "s1", "q?", "opus"):
            pass


def test_open_crashed_session_cannot_be_reopened(tmp_path):
    """Une session en status='open' (crash non scellé) refuse aussi le ré-ouverture."""
    import json

    import duckdb

    db = tmp_path / "ep_crash.duckdb"
    # Simulate a crashed session by inserting an 'open' row directly via raw connection
    con = duckdb.connect(str(db))
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS sessions ("
            "session_id VARCHAR PRIMARY KEY, "
            "question VARCHAR, model VARCHAR, "
            "started_at TIMESTAMP, ended_at TIMESTAMP, "
            "status VARCHAR, meta VARCHAR)"
        )
        con.execute(
            "CREATE TABLE IF NOT EXISTS nodes ("
            "id VARCHAR PRIMARY KEY, session_id VARCHAR, "
            "seq INTEGER, parent_id VARCHAR, kind VARCHAR, "
            "content VARCHAR, meta VARCHAR, ts TIMESTAMP)"
        )
        con.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                "s1",
                "q?",
                "opus",
                datetime.now(timezone.utc),
                None,
                "open",
                json.dumps({}),
            ],
        )
    finally:
        con.close()

    # Now trying to open the same session_id must be refused
    with pytest.raises(ValueError, match="immuable"):
        with Scribe(db, "s1", "q?", "opus"):
            pass


def test_load_remplit_le_ts_des_noeuds(tmp_path):
    db = tmp_path / "t.duckdb"
    with Scribe(db, "s1", "q", "opus") as scribe:
        scribe.record_nodes([("essai", {"x": 1}, {})])
    trace = load(db, "s1")
    horodates = [n.ts for n in trace.nodes if n.ts is not None]
    assert len(horodates) == len(trace.nodes)  # le store date TOUS les nœuds
    assert horodates == sorted(horodates)  # ordonnés comme les seq


def test_ts_relu_est_aware_utc_et_conserve_l_instant(tmp_path):
    """Le ts relu est aware UTC et vaut l'instant RÉEL de l'écriture.

    Garde anti-régression du défaut d'heure locale : la colonne DuckDB est
    ``TIMESTAMP`` (sans fuseau), donc insérer un datetime *aware* le faisait
    convertir vers le fuseau de session puis dépouiller — la base portait de
    l'heure locale, et les écarts d'une session à cheval sur un changement
    d'heure étaient faux de ±1 h.
    """
    avant = datetime.now(timezone.utc)
    db = tmp_path / "t.duckdb"
    with Scribe(db, "s1", "q", "opus") as scribe:
        scribe.record_nodes([("essai", {"x": 1}, {})])
    apres = datetime.now(timezone.utc)

    trace = load(db, "s1")
    horodates = [n.ts for n in trace.nodes]
    assert all(t is not None for t in horodates)
    for t in horodates:
        assert t is not None
        assert t.tzinfo is not None, "le ts relu doit être timezone-aware"
        assert t.utcoffset() == timedelta(0), "le ts relu doit être en UTC"
        # comparaison directe avec des datetime aware : plus aucun monde séparé
        assert avant <= t <= apres, (
            f"instant hors de la fenêtre réelle d'écriture : {t.isoformat()}"
        )
