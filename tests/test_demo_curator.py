"""Vérifie que la fin de séance du curateur ne se tait jamais (gate humain)."""

import json

import duckdb

from intreepid.demo_curator import _attribution, _preuve_et_mesures
from intreepid.scribe.store import Scribe, load


def test_base_sans_session_le_dit_explicitement(tmp_path):
    """Une trace présente mais vide doit produire un constat, pas un silence."""
    db = tmp_path / "vide.duckdb"
    con = duckdb.connect(str(db))
    try:
        con.execute("CREATE TABLE sessions (session_id VARCHAR)")
    finally:
        con.close()

    out = _preuve_et_mesures(db)
    assert "AUCUNE session" in out
    assert "à signaler au gate" in out


def test_session_reelle_rend_preuve_et_mesures(tmp_path):
    """Une session scellée rend le bloc de preuve ET le bloc de mesures."""
    db = tmp_path / "vraie.duckdb"
    with Scribe(db, "s1", "q", "opus") as sc:
        sc.record_nodes(
            [
                ("human_turn", {"text": "ma réponse"}, {"actor": "human"}),
                (
                    "curation_validated",
                    {"path": "catalog/x.fiche.yaml", "dataset": "x"},
                    {"hash": "abc123def456", "actor": "human"},
                ),
            ]
        )

    out = _preuve_et_mesures(db)
    assert "preuve greffier" in out
    assert "statut session" in out and "closed" in out
    assert "tours humains            : 1" in out
    assert "nœuds curation_validated : 1" in out
    assert "mesures" in out


_BLOC = (
    '```json\n{"fiche_delta": {"columns": {"a": {}}},'
    ' "proposes_completion": false}\n```'
)


def test_attribution_separe_prose_et_delta(tmp_path):
    """Le critère principal du gate #10 : le brouillon cesse-t-il de dominer ?

    `scribe/metrics.py` agrège le tour ENTIER et ne peut pas répondre — il est
    agnostique du rôle. Le calcul vit ici et réutilise le parseur du curateur.
    """
    db = tmp_path / "attr.duckdb"
    with Scribe(db, "s1", "q", "opus") as sc:
        sc.record_nodes(
            [
                ("agent_turn", {"text": f"Bonjour.\n{_BLOC}"}, {"actor": "agent"}),
                ("agent_turn", {"text": f"Suite.\n{_BLOC}"}, {"actor": "agent"}),
            ]
        )

    texte = _attribution(load(db, "s1"))
    assert "#1  prose 8 car. · questions 0 car. · delta 82 car." in texte
    assert "#2  prose 6 car. · questions 0 car. · delta 82 car." in texte
    assert "total : prose 14 · questions 0 · delta 164 (92 %" in texte


def test_attribution_tolere_un_tour_sans_bloc(tmp_path):
    """Un tour sans bloc JSON compte 0 caractère de delta.

    Repli tolérant de `turn.py` : sans bloc, tout le texte est le message. Le
    rapport ne doit pas planter pour autant.
    """
    db = tmp_path / "nobloc.duckdb"
    with Scribe(db, "s1", "q", "opus") as sc:
        sc.record_nodes([("agent_turn", {"text": "que de la prose"}, {})])

    assert "delta 0 car." in _attribution(load(db, "s1"))


def test_attribution_sans_tour_dagent_le_dit(tmp_path):
    """Une trace sans tour d'agent le dit, au lieu d'afficher un 0 % trompeur.

    C'est le cas d'une trace d'analyste one-shot, qui n'a aucun `agent_turn`.
    """
    db = tmp_path / "vide.duckdb"
    with Scribe(db, "s1", "q", "opus") as sc:
        sc.record_nodes([("human_turn", {"text": "o"}, {"actor": "human"})])

    assert "aucun tour d'agent" in _attribution(load(db, "s1")).lower()


def test_attribution_isole_les_questions(tmp_path):
    """Trois postes : prose, questions, fiche — la compensation doit se voir."""
    db = tmp_path / "t.duckdb"
    texte = (
        "Deux jugements vous reviennent.\n"
        '```json\n{"fiche_delta": {"columns": {"a": {"sens": "x"}}},'
        ' "questions": [{"n": 1, "colonne": "a", "constat": "c"}],'
        ' "proposes_completion": false}\n```'
    )
    with Scribe(db, "s1", "q", "opus") as sc:
        sc.record_nodes([("agent_turn", {"text": texte}, {"actor": "agent"})])
    tr = load(db, "s1")
    out = _attribution(tr)
    assert "questions" in out
    assert "prose" in out and "delta" in out
    # Les CHIFFRES, pas seulement la présence des mots : le critère 3 du gate
    # (médiane ≤ 800 car.) repose entièrement sur cette arithmétique, et le
    # garde-fou D5 n'autorise qu'une séance. 42 = len(json.dumps) de la
    # question ; 2 = ses caractères rédigés (`a` + `c`, le `n` entier exclu).
    assert "questions 42 car." in out
    assert "médiane par question : 2 car." in out


def test_mediane_est_bien_une_mediane_et_ignore_la_syntaxe_json(tmp_path):
    """TROIS questions très inégales : aucune autre statistique ne donne 10.

    Deux valeurs ne suffiraient pas — à 2 et 182, médiane ET moyenne valent
    92, et une confusion des deux passerait inaperçue. C'est exactement
    l'erreur qui fausserait le critère 3 du gate : sur sept questions dont une
    énorme, moyenne et médiane divergent franchement. Ici, caractères rédigés
    2 · 10 · 182 → médiane 10, moyenne 64, maximum 182, somme 194.
    """
    db = tmp_path / "med.duckdb"
    texte = (
        "Trois questions.\n```json\n"
        + json.dumps(
            {
                "questions": [
                    {"n": 1, "colonne": "a", "constat": "c"},
                    {"n": 2, "colonne": "bb", "constat": "d" * 8},
                    {
                        "n": 3,
                        "colonne": "bb",
                        "constat": "x" * 100,
                        "enjeu": "y" * 50,
                        "options": {"a": "z" * 30},
                    },
                ],
                "proposes_completion": False,
            },
            ensure_ascii=False,
        )
        + "\n```"
    )
    with Scribe(db, "s1", "q", "opus") as sc:
        sc.record_nodes([("agent_turn", {"text": texte}, {"actor": "agent"})])

    out = _attribution(load(db, "s1"))
    assert "médiane par question : 10 car." in out, out
