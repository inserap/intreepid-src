"""Vérifie le rendu ASCII lisible d'un arbre de session (démo + inspection)."""

from intreepid.scribe.render import _short, render
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


def test_short_truncates_long_text():
    long_text = "a" * 101
    result = _short(long_text)
    assert result.endswith("…")
    assert len(result) == 100  # limit - 1 chars + "…"


def test_short_preserves_short_text():
    short_text = "hello"
    assert _short(short_text) == "hello"


def test_short_exactly_at_limit():
    text = "a" * 100
    result = _short(text)
    assert result == text  # exactly 100 chars — no truncation
