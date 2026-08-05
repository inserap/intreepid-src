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


def _node(seq, kind, content, meta=None, offset_s=0.0, parent_id="s#0"):
    return TraceNode(
        id=f"s#{seq}",
        session_id="s",
        seq=seq,
        parent_id=parent_id,
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


def test_mesure_par_tour_et_temps_hors_api() -> None:
    m = summarize(_trace([_tour(1, 0.0), _tour(2, 200.0, cost=0.02)]))
    assert len(m.turns) == 2
    assert m.turns[0].non_api_ms == 40_000  # duration_ms - duration_api_ms
    assert m.turns[0].output_tokens == 5
    assert m.total_cost_usd == 0.03
    assert m.total_api_ms == 120_000
    assert m.total_non_api_ms == 80_000


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
            parent_id="s#1",
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
        2,
        "tool_result",
        {"content": "", "is_error": False},
        {"tool_use_id": "t1"},
        1.0,
        parent_id="s#1",
    )
    n1.ts = None
    m = summarize(_trace([n1, n2]))
    assert m.tools[0].duration_ms is None
    # un seul instant connu ne fait pas une durée : elle est INCONNUE, pas nulle
    assert m.wall_ms is None


def test_trace_vide_ne_leve_pas() -> None:
    m = summarize(_trace([]))
    assert m.turns == []
    assert m.tools == []
    assert m.wall_ms is None
    assert m.total_cost_usd is None
    assert m.total_api_ms is None
    assert m.total_non_api_ms is None
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


def test_trace_sans_tour_avec_outils_affiche_inconnu() -> None:
    # Défaut bloquant : sans tour et sans méta de coût, les totaux doivent
    # s'afficher "?" (None), pas 0. La trace contient des appels d'outil réels.
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
            {"content": "ok", "is_error": False},
            {"tool_use_id": "t1"},
            5.0,
            parent_id="s#1",
        ),
    ]
    m = summarize(_trace(nodes))
    assert m.degraded is False
    assert m.turns == []
    assert m.total_cost_usd is None
    assert m.total_api_ms is None
    assert m.total_non_api_ms is None
    texte = render_metrics(m)
    # Le total doit s'afficher "?" et non "0.0000 USD"
    assert "0.0000 USD" not in texte
    assert "?" in texte


def test_bout_en_bout_capture_relecture_mesure(tmp_path) -> None:
    # Les tests ci-dessus opèrent sur des ts construits à la main ; ce test ferme
    # l'écart en exerçant le chemin réel capture -> DuckDB -> load -> summarize,
    # sans aucun appel LLM. Depuis le passage à l'UTC, load rend des datetime
    # AWARE : les deux mondes n'en font plus qu'un.
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
    assert m.turns[0].non_api_ms == 3000
    assert m.turns[0].output_tokens == 400
    assert m.total_cost_usd == 0.031
    assert [t.name for t in m.tools] == ["profile_raw"]
    assert m.tools[0].duration_ms is not None  # ts réels relus, soustraction possible
    assert m.wall_ms is not None


def test_appels_simultanes_ne_sont_pas_comptes_deux_fois() -> None:
    """Deux appels d'un même message ne consomment qu'UNE fois leur intervalle.

    ``_insert`` horodate nœud par nœud : les ts de deux ToolUseBlock d'un même
    message sont voisins, jamais égaux. Chaque durée vaut donc ~le même
    intervalle, et les SOMMER le comptait deux fois.
    """
    nodes = [
        _node(1, "tool_call", {"name": "a", "input": {}}, offset_s=0.0),
        _node(2, "tool_call", {"name": "b", "input": {}}, offset_s=0.001),
        _node(
            3,
            "tool_result",
            {"content": "ok", "is_error": False},
            parent_id="s#1",
            offset_s=2.0,
        ),
        _node(
            4,
            "tool_result",
            {"content": "ok", "is_error": False},
            parent_id="s#2",
            offset_s=2.001,
        ),
    ]
    m = summarize(_trace(nodes))
    assert m.total_tool_measured_ms is not None
    # l'intervalle réellement écoulé est ~2 s, pas ~4 s
    assert 1_900 <= m.total_tool_measured_ms <= 2_100, m.total_tool_measured_ms


def test_appels_sequentiels_additionnent_leurs_durees() -> None:
    """Deux appels disjoints comptent chacun pour leur propre durée."""
    nodes = [
        _node(1, "tool_call", {"name": "a", "input": {}}, offset_s=0.0),
        _node(
            2,
            "tool_result",
            {"content": "ok", "is_error": False},
            parent_id="s#1",
            offset_s=1.0,
        ),
        _node(3, "tool_call", {"name": "b", "input": {}}, offset_s=5.0),
        _node(
            4,
            "tool_result",
            {"content": "ok", "is_error": False},
            parent_id="s#3",
            offset_s=8.0,
        ),
    ]
    m = summarize(_trace(nodes))
    assert m.total_tool_measured_ms == 4_000.0  # 1 s + 3 s, intervalles disjoints


def test_minorant_de_cout_quand_un_tour_na_pas_de_cout() -> None:
    """Deux tours dont un sans coût : le total est un MINORANT, pas une vérité."""
    tour_sans_cout = _node(
        2,
        "turn_result",
        {
            "duration_ms": 100_000,
            "duration_api_ms": 60_000,
            "num_turns": 1,
            "total_cost_usd": None,
            "usage": {"input_tokens": 10, "output_tokens": 5},
            "terminal_reason": "completed",
        },
        offset_s=100.0,
    )
    out = render_metrics(summarize(_trace([_tour(1, 0.0, cost=0.02), tour_sans_cout])))
    assert "≥ 0.0200 USD" in out
    assert "1 tour(s) sans coût" in out


def test_appel_en_erreur_est_signale() -> None:
    nodes = [
        _node(1, "tool_call", {"name": "a", "input": {}}, offset_s=0.0),
        _node(
            2,
            "tool_result",
            {"content": "boom", "is_error": True},
            parent_id="s#1",
            offset_s=1.0,
        ),
    ]
    out = render_metrics(summarize(_trace(nodes)))
    assert "[erreur]" in out


def test_appel_non_apparie_nest_pas_declare_sans_erreur() -> None:
    """is_error inconnu ne doit pas se lire comme « appel réussi »."""
    nodes = [_node(1, "tool_call", {"name": "a", "input": {}}, offset_s=0.0)]
    out = render_metrics(summarize(_trace(nodes)))
    assert "[erreur]" not in out
    assert "[sans résultat]" in out


def test_wall_ms_inconnu_avec_un_seul_horodatage() -> None:
    """Un seul instant connu ne fait pas une durée de 0 s : elle est INCONNUE."""
    m = summarize(_trace([_node(1, "essai", {"x": 1}, offset_s=0.0)]))
    assert m.wall_ms is None
    assert "bout en bout : ?" in render_metrics(m)


def test_aucun_residu_negatif_dans_le_rendu() -> None:
    """Hors-API (horloge SDK) et durées d'outil (greffier) ne se soustraient pas."""
    nodes = [
        _tour(1, 0.0, dur=5_000, api=2_600),  # hors API = 2,4 s
        _node(2, "tool_call", {"name": "a", "input": {}}, offset_s=0.0),
        _node(
            3,
            "tool_result",
            {"content": "ok", "is_error": False},
            parent_id="s#2",
            offset_s=3.1,  # outil mesuré 3,1 s > hors API 2,4 s
        ),
    ]
    out = render_metrics(summarize(_trace(nodes)))
    assert "-0" not in out, f"résidu négatif dans le rendu :\n{out}"
    assert "démarrage" not in out
    # les deux chiffres cohabitent, chacun avec son horloge nommée
    assert "hors API (horloge SDK)" in out
    assert "outils mesurés (horodatages greffier)" in out


def test_tokens_de_cache_sont_affiches() -> None:
    """Taire le cache donne une image fausse de l'entrée (6 facturés, 43 781 lus)."""
    tour = _node(
        1,
        "turn_result",
        {
            "duration_ms": 141_200,
            "duration_api_ms": 138_800,
            "num_turns": 1,
            "total_cost_usd": 0.4194,
            "usage": {
                "input_tokens": 6,
                "output_tokens": 9_939,
                "cache_read_input_tokens": 43_781,
                "cache_creation_input_tokens": 14_900,
            },
            "terminal_reason": "completed",
        },
        offset_s=0.0,
    )
    m = summarize(_trace([tour]))
    assert m.turns[0].cache_read_tokens == 43_781
    assert m.turns[0].cache_creation_tokens == 14_900
    assert "cache 43781 lus / 14900 créés" in render_metrics(m)


def test_cache_absent_saffiche_inconnu_pas_zero() -> None:
    m = summarize(_trace([_tour(1, 0.0)]))  # usage sans clés de cache
    assert m.turns[0].cache_read_tokens is None
    assert "cache ?" in render_metrics(m)


def test_attribution_de_la_sortie_prose_vs_thinking() -> None:
    """La sortie devient attribuable : prose lue par l'humain vs thinking."""
    nodes = [
        _node(1, "thinking", {"text": "x" * 8_396}, offset_s=0.0),
        _node(2, "agent_turn", {"text": "y" * 1_200}, {"actor": "agent"}, 1.0),
        _tour(3, 2.0),
    ]
    m = summarize(_trace(nodes))
    assert m.thinking_chars == 8_396
    assert m.prose_chars == 1_200
    out = render_metrics(m)
    assert "prose" in out and "thinking" in out


def test_attribution_inconnue_sans_noeud_dedie() -> None:
    """Une trace d'analyste one-shot ne porte aucun agent_turn : None, pas 0."""
    m = summarize(_trace([_tour(1, 0.0)]))
    assert m.prose_chars is None
    assert m.thinking_chars is None


def test_resultat_sans_appel_connu_ne_casse_pas_l_appariement() -> None:
    """Un tool_result parenté à la racine (appel inconnu) est ignoré sans erreur.

    Le builder retombe sur la racine quand il ne retrouve pas l'appel ; l'ancien
    appariement par tool_use_id le laissait aussi de côté, la nouvelle mécanique
    par parenté ne doit pas le confondre avec un appel.
    """
    nodes = [
        _node(1, "tool_call", {"name": "a", "input": {}}, offset_s=0.0),
        _node(
            2,
            "tool_result",
            {"content": "orphelin", "is_error": False},
            parent_id="s#0",
            offset_s=1.0,
        ),
    ]
    m = summarize(_trace(nodes))
    assert len(m.tools) == 1
    assert m.tools[0].duration_ms is None  # non apparié => durée inconnue
    assert m.total_tool_measured_ms is None
