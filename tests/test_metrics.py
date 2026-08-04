"""Vérifie la projection d'une trace en mesures (durées, coût, appels d'outil)."""

from datetime import datetime, timedelta, timezone

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from intreepid.scribe.metrics import render_metrics, summarize
from intreepid.scribe.store import Scribe, load
from intreepid.scribe.trace import SessionTrace, TraceNode

_T0 = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)


def _node(seq, kind, content, meta=None, offset_s=0.0):
    return TraceNode(
        id=f"s#{seq}",
        session_id="s",
        seq=seq,
        parent_id="s#0",
        kind=kind,
        content=content,
        meta=meta or {},
        ts=_T0 + timedelta(seconds=offset_s),
    )


def _trace(nodes):
    return SessionTrace(
        session_id="s", question="q", model="opus", status="closed", nodes=nodes
    )


def _tour(seq, offset_s, cost=0.01, dur=100_000, api=60_000):
    return _node(
        seq,
        "turn_result",
        {
            "duration_ms": dur,
            "duration_api_ms": api,
            "num_turns": 1,
            "total_cost_usd": cost,
            "usage": {"input_tokens": 10, "output_tokens": 5},
            "terminal_reason": "completed",
        },
        offset_s=offset_s,
    )


def test_mesure_par_tour_et_temps_hors_llm() -> None:
    m = summarize(_trace([_tour(1, 0.0), _tour(2, 200.0, cost=0.02)]))
    assert len(m.turns) == 2
    assert m.turns[0].tool_ms == 40_000  # duration_ms - duration_api_ms
    assert m.turns[0].output_tokens == 5
    assert m.total_cost_usd == 0.03
    assert m.total_api_ms == 120_000
    assert m.total_tool_ms == 80_000


def test_duree_d_un_appel_d_outil_par_appariement() -> None:
    nodes = [
        _node(
            1,
            "tool_call",
            {"name": "profile_raw", "input": {}},
            {"tool_use_id": "t1"},
            0.0,
        ),
        _node(
            2,
            "tool_result",
            {"content": "x", "is_error": False},
            {"tool_use_id": "t1"},
            12.5,
        ),
    ]
    m = summarize(_trace(nodes))
    assert len(m.tools) == 1
    assert m.tools[0].name == "profile_raw"
    assert m.tools[0].duration_ms == 12_500
    assert m.tools[0].is_error is False
    assert m.calls_by_tool == {"profile_raw": 1}


def test_appel_sans_resultat_donne_une_duree_inconnue() -> None:
    nodes = [
        _node(
            1,
            "tool_call",
            {"name": "profile_raw", "input": {}},
            {"tool_use_id": "t1"},
            0.0,
        )
    ]
    m = summarize(_trace(nodes))
    assert m.tools[0].duration_ms is None  # session avortée : jamais une exception
    assert m.calls_by_tool == {"profile_raw": 1}


def test_noeud_sans_ts_ne_casse_pas_la_mesure() -> None:
    # en capture (hors relecture) ts vaut None : la durée est inconnue, pas fausse
    n1 = _node(1, "tool_call", {"name": "x", "input": {}}, {"tool_use_id": "t1"}, 0.0)
    n2 = _node(
        2, "tool_result", {"content": "", "is_error": False}, {"tool_use_id": "t1"}, 1.0
    )
    n1.ts = None
    m = summarize(_trace([n1, n2]))
    assert m.tools[0].duration_ms is None
    assert m.wall_ms is not None


def test_trace_vide_ne_leve_pas() -> None:
    m = summarize(_trace([]))
    assert m.turns == []
    assert m.tools == []
    assert m.wall_ms is None
    assert m.total_cost_usd == 0.0
    assert m.degraded is False


def test_trace_anterieure_repli_sur_la_meta_de_session() -> None:
    # aucune trace écrite avant cette slice n'a de nœud turn_result : le coût est
    # pourtant dans la méta scellée. Mesure DÉGRADÉE (aucune durée), pas nulle.
    trace = SessionTrace(
        session_id="s",
        question="q",
        model="opus",
        status="closed",
        nodes=[],
        meta={"num_turns": 4, "total_cost_usd": 0.42, "terminal_reason": "completed"},
    )
    m = summarize(trace)
    assert m.degraded is True
    assert m.total_cost_usd == 0.42
    assert m.turns[0].duration_ms is None
    assert "dégradée" in render_metrics(m)


def test_rendu_texte_porte_les_totaux() -> None:
    m = summarize(_trace([_tour(1, 0.0)]))
    texte = render_metrics(m)
    assert "profile_raw" not in texte  # aucun outil dans cette trace
    assert "tour" in texte.lower()
    assert "0.01" in texte


def test_bout_en_bout_capture_relecture_mesure(tmp_path) -> None:
    # Les 6 tests ci-dessus opèrent sur des ts timezone-AWARE construits à la main ;
    # le chemin réel (DuckDB) rend des datetime NAÏFS. Ce test ferme l'écart en
    # exerçant capture -> DuckDB -> load -> summarize, sans aucun appel LLM.
    db = tmp_path / "t.duckdb"
    with Scribe(db, "s1", "q", "opus") as sc:
        sc.record(
            AssistantMessage(
                content=[ToolUseBlock(id="t1", name="profile_raw", input={})],
                model="opus",
            )
        )
        sc.record(
            UserMessage(content=[ToolResultBlock(tool_use_id="t1", content="ok")])
        )
        sc.record(
            ResultMessage(
                subtype="success",
                duration_ms=8000,
                duration_api_ms=5000,
                is_error=False,
                num_turns=1,
                session_id="s1",
                total_cost_usd=0.031,
                usage={"input_tokens": 1200, "output_tokens": 400},
                terminal_reason="completed",
            )
        )
    m = summarize(load(db, "s1"))
    assert m.degraded is False
    assert len(m.turns) == 1
    assert m.turns[0].tool_ms == 3000
    assert m.turns[0].output_tokens == 400
    assert m.total_cost_usd == 0.031
    assert [t.name for t in m.tools] == ["profile_raw"]
    assert m.tools[0].duration_ms is not None  # ts réels relus, soustraction possible
    assert m.wall_ms is not None
