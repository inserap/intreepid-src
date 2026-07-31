"""Vérifie le rendu ASCII lisible d'un arbre de session (démo + inspection)."""

from intreepid.scribe.render import render
from intreepid.scribe.trace import SessionTrace, TraceNode


def _trace():
    return SessionTrace(
        session_id="s1",
        question="ma question",
        model="opus",
        status="closed",
        nodes=[
            TraceNode(
                "s1#0",
                "s1",
                0,
                None,
                "session_root",
                {"question": "ma question", "model": "opus"},
            ),
            TraceNode("s1#1", "s1", 1, "s1#0", "thinking", {"text": "hypothèse"}),
            TraceNode(
                "s1#2",
                "s1",
                2,
                "s1#0",
                "tool_call",
                {"name": "profile_stats", "input": {"c": "x"}},
                {"tool_use_id": "t1"},
            ),
            TraceNode(
                "s1#3",
                "s1",
                3,
                "s1#2",
                "tool_result",
                {"content": "agrégat", "is_error": None},
                {"tool_use_id": "t1"},
            ),
            TraceNode(
                "s1#4",
                "s1",
                4,
                "s1#0",
                "observation",
                {"claim": "refus", "note": "causalité"},
                {"statut": "refusé"},
            ),
        ],
    )


def test_render_contains_structure():
    out = render(_trace())
    assert "s1" in out and "[closed]" in out
    assert "hypothèse" in out
    assert "profile_stats" in out
    assert "agrégat" in out
    assert "refusé" in out and "refus" in out


def test_render_result_nested_under_call():
    lines = render(_trace()).splitlines()
    call_i = next(i for i, ln in enumerate(lines) if "profile_stats" in ln)
    res_i = next(i for i, ln in enumerate(lines) if "agrégat" in ln)
    assert res_i == call_i + 1  # le résultat suit immédiatement son appel
