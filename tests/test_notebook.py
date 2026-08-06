"""Golden déterministe du générateur de notebook (to_quarto, pur)."""

from intreepid.scribe.notebook import to_quarto
from intreepid.scribe.trace import SessionTrace, TraceNode


def _trace() -> SessionTrace:
    sid = "s1"
    nodes = [
        TraceNode(
            f"{sid}#0",
            sid,
            0,
            None,
            "session_root",
            {"question": "Q?", "model": "opus"},
        ),
        TraceNode(f"{sid}#1", sid, 1, f"{sid}#0", "thinking", {"text": "je réfléchis"}),
        TraceNode(
            f"{sid}#2",
            sid,
            2,
            f"{sid}#0",
            "tool_call",
            {"name": "profile_stats", "input": {"columns": ["c"]}},
            {"tool_use_id": "t1"},
        ),
        TraceNode(
            f"{sid}#3",
            sid,
            3,
            f"{sid}#2",
            "tool_result",
            {"content": '{"c": {"type": "categorical"}}', "is_error": False},
            {"tool_use_id": "t1"},
        ),
        TraceNode(
            f"{sid}#4",
            sid,
            4,
            f"{sid}#0",
            "observation",
            {"claim": "unite A sur-concentree", "note": "pseudo_p=0.001"},
            {"statut": "fait", "confiance": "haute"},
        ),
        TraceNode(
            f"{sid}#5",
            sid,
            5,
            f"{sid}#0",
            "observation",
            {"claim": "lien X->Y", "note": "non croise"},
            {"statut": "refusé", "confiance": "basse"},
        ),
        TraceNode(
            f"{sid}#6",
            sid,
            6,
            f"{sid}#0",
            "observation",
            {"claim": "saisonnalite ?", "note": None},
            {"statut": "hypothèse", "confiance": "moyenne"},
        ),
    ]
    return SessionTrace(
        sid,
        "Q?",
        "opus",
        "closed",
        nodes,
        {"num_turns": 3, "total_cost_usd": 0.12, "terminal_reason": "end_turn"},
    )


def test_frontmatter_and_title():
    q = to_quarto(_trace())
    assert q.startswith("---")
    assert 'title: "Q?"' in q
    assert "embed-resources: true" in q


def test_tool_call_and_result_rendered():
    q = to_quarto(_trace())
    assert "`profile_stats`" in q
    assert '"columns"' in q
    assert "categorical" in q


def test_observation_callouts_by_statut():
    q = to_quarto(_trace())
    assert ".callout-note" in q  # fait
    assert ".callout-caution" in q  # refusé
    assert ".callout-warning" in q  # hypothèse
    assert "unite A sur-concentree" in q


def test_meta_footer():
    q = to_quarto(_trace())
    assert "tours : 3" in q
    assert "end_turn" in q


def test_pure_total_on_unknown_kind():
    sid = "s2"
    tr = SessionTrace(
        sid,
        "Q",
        "opus",
        "closed",
        [
            TraceNode(
                f"{sid}#0",
                sid,
                0,
                None,
                "session_root",
                {"question": "Q", "model": "opus"},
            ),
            TraceNode(f"{sid}#1", sid, 1, f"{sid}#0", "weird_kind", {"x": 1}),
        ],
        {},
    )
    out = to_quarto(tr)  # ne doit PAS lever
    assert "non rendu" in out


def test_turn_result_noeud_non_rendu_dans_notebook():
    # Garde de non-régression : un nœud turn_result ne doit rien émettre dans le
    # notebook. Sans cette garde, une régression future réinjecterait un commentaire
    # parasite par tour (ex. "<!-- nœud non rendu : kind=turn_result -->").
    sid = "s3"
    tr = SessionTrace(
        sid,
        "Q",
        "opus",
        "closed",
        [
            TraceNode(
                f"{sid}#0",
                sid,
                0,
                None,
                "session_root",
                {"question": "Q", "model": "opus"},
            ),
            TraceNode(
                f"{sid}#1",
                sid,
                1,
                f"{sid}#0",
                "turn_result",
                {
                    "duration_ms": 5000,
                    "duration_api_ms": 3000,
                    "num_turns": 1,
                    "total_cost_usd": 0.01,
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                    "terminal_reason": "end_turn",
                },
            ),
        ],
        {},
    )
    out = to_quarto(tr)
    assert "turn_result" not in out


def test_tours_de_conversation_non_rendus_dans_notebook():
    """Garde : agent_turn / human_turn n'émettent aucun commentaire parasite.

    Le notebook projette une session d'ANALYSE ; les tours d'une conversation
    n'y ont pas de place. Sans cette garde, chaque tour produit un
    "<!-- nœud non rendu : kind=agent_turn -->" (défaut latent depuis #7c
    pour human_turn).
    """
    trace = SessionTrace(
        session_id="s",
        question="q",
        model="opus",
        status="closed",
        nodes=[
            TraceNode(
                id="s#1",
                session_id="s",
                seq=1,
                parent_id="s#0",
                kind="agent_turn",
                content={"text": "ma question"},
                meta={"actor": "agent"},
            ),
            TraceNode(
                id="s#2",
                session_id="s",
                seq=2,
                parent_id="s#0",
                kind="human_turn",
                content={"text": "ma réponse"},
                meta={"actor": "human"},
            ),
        ],
    )
    out = to_quarto(trace)
    assert "non rendu" not in out
    assert "agent_turn" not in out
    assert "human_turn" not in out


def test_render_html_degrades_without_quarto(monkeypatch, tmp_path):
    import intreepid.scribe.notebook as nb

    def boom(*a, **k):
        raise FileNotFoundError("quarto")

    monkeypatch.setattr(nb.subprocess, "run", boom)
    qmd = tmp_path / "x.qmd"
    qmd.write_text("---\n---\n", encoding="utf-8")
    assert nb.render_html(qmd) is None
