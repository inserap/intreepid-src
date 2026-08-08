"""Vérifie les trois fonctions pures du canal de questions du curateur."""

from typing import Any

from intreepid.agent.curator.questions import (
    attach_answers,
    merge_questions,
    render_question,
)


def test_merge_ajoute_les_questions_neuves() -> None:
    acc = [{"n": 1, "colonne": "a"}]
    out = merge_questions(acc, [{"n": 2, "colonne": "b"}])
    assert [q["n"] for q in out] == [1, 2]


def test_merge_revise_par_numero_derniere_ecriture_gagne() -> None:
    acc = [{"n": 1, "colonne": "a", "enjeu": "vieux"}]
    out = merge_questions(acc, [{"n": 1, "colonne": "a", "enjeu": "neuf"}])
    assert len(out) == 1
    assert out[0]["enjeu"] == "neuf"


def test_merge_ne_mute_pas_laccumulateur() -> None:
    acc = [{"n": 1, "colonne": "a"}]
    merge_questions(acc, [{"n": 1, "colonne": "z"}])
    assert acc == [{"n": 1, "colonne": "a"}]


def test_merge_delta_vide_ou_none_rend_laccumulateur() -> None:
    acc = [{"n": 1}]
    assert merge_questions(acc, None) == acc
    assert merge_questions(acc, []) == acc
    assert merge_questions(None, None) == []


def test_merge_ignore_les_entrees_non_dict() -> None:
    out = merge_questions(None, [{"n": 1}, "pas un dict", 42])  # type: ignore[list-item]
    assert out == [{"n": 1}]


def test_merge_conserve_lordre_des_numeros_inconnus() -> None:
    """Une question sans `n` n'est pas jetée : elle est ajoutée en fin."""
    out = merge_questions([{"n": 1}], [{"colonne": "sans_numero"}])
    assert len(out) == 2
    assert out[1]["colonne"] == "sans_numero"


def test_render_porte_les_elements_de_la_question() -> None:
    q: dict[str, Any] = {
        "n": 3,
        "colonne": "code_statut",
        "constat": "6 valeurs distinctes sur 40 000 lignes.",
        "enjeu": "Une moyenne de 2,3 qui ne veut rien dire.",
        "options": {"a": "code catégoriel", "b": "vraie mesure"},
        "penchant": "a",
        "pourquoi": "6 valeurs sur 40 000 lignes.",
    }
    out = render_question(q, position=1, total=7)
    assert "Question 1/7" in out
    # le numéro de l'AGENT en plus de la progression : sans lui, il dit
    # « répondez 3a » quand l'écran annonce « Question 1/7 »
    assert "(n° 3)" in out
    assert "code_statut" in out
    assert "6 valeurs distinctes sur 40 000 lignes." in out
    assert "Une moyenne de 2,3 qui ne veut rien dire." in out
    assert "(a) code catégoriel" in out
    assert "(b) vraie mesure" in out
    assert "je ne sais pas" in out


def test_render_sans_options_ne_plante_pas() -> None:
    out = render_question({"n": 1, "constat": "un constat"}, position=1, total=1)
    assert "un constat" in out
    assert "je ne sais pas" in out


def test_render_dune_entree_tordue_ne_plante_pas() -> None:
    """Options non-dict, champs absents : on affiche ce qu'il y a."""
    q: dict[str, Any] = {"options": ["a", "b"], "constat": None}
    out = render_question(q, position=2, total=3)
    assert "Question 2/3" in out
    assert "n°" not in out  # pas de `n` => pas de numéro inventé


def test_attach_associe_les_reponses_par_numero() -> None:
    qs = [{"n": 1, "colonne": "a"}, {"n": 2, "colonne": "b"}]
    out = attach_answers(qs, {1: "1a"})
    assert out[0]["reponse"] == "1a"
    assert out[1]["reponse"] is None


def test_attach_ne_mute_pas_lentree() -> None:
    qs = [{"n": 1}]
    attach_answers(qs, {1: "x"})
    assert "reponse" not in qs[0]
