"""Vérifie l'accumulation du brouillon de fiche hors de l'agent (Q-0023)."""

from intreepid.agent.curator.draft import inventory_line, merge_delta


def test_delta_sur_accumulateur_vide() -> None:
    out = merge_delta(None, {"dataset": "d", "columns": {"a": {"type": "numeric"}}})
    assert out["dataset"] == "d"
    assert out["columns"] == {"a": {"type": "numeric"}}


def test_colonne_nouvelle_nefface_pas_les_precedentes() -> None:
    """Le test central de la fusion.

    Sans fusion entrée par entrée, `columns` serait remplacé en bloc et la
    colonne tranchée au tour précédent disparaîtrait.
    """
    acc = {"columns": {"a": {"type": "numeric"}}}
    out = merge_delta(acc, {"columns": {"b": {"type": "categorical"}}})
    assert set(out["columns"]) == {"a", "b"}
    assert out["columns"]["a"] == {"type": "numeric"}


def test_colonne_corrigee_derniere_ecriture_gagne() -> None:
    acc = {"columns": {"a": {"type": "numeric"}}}
    out = merge_delta(acc, {"columns": {"a": {"type": "categorical"}}})
    assert out["columns"]["a"] == {"type": "categorical"}


def test_cle_de_haut_niveau_ecrasee() -> None:
    out = merge_delta({"titre": "ancien"}, {"titre": "nouveau"})
    assert out["titre"] == "nouveau"


def test_delta_none_ou_vide_laisse_laccumulateur_intact() -> None:
    acc = {"dataset": "d", "columns": {"a": {"type": "numeric"}}}
    assert merge_delta(acc, None) == acc
    assert merge_delta(acc, {}) == acc


def test_columns_non_dict_est_ignore() -> None:
    """Un `columns` non-dict n'efface rien.

    Repli tolérant, cohérent avec `turn.py` : un modèle qui envoie une liste ne
    doit ni effacer l'accumulateur ni faire planter la séance.
    """
    acc = {"columns": {"a": {"type": "numeric"}}}
    out = merge_delta(acc, {"columns": ["a", "b"], "titre": "t"})
    assert out["columns"] == {"a": {"type": "numeric"}}
    assert out["titre"] == "t"


def test_merge_ne_mute_pas_ses_arguments() -> None:
    acc = {"columns": {"a": {"type": "numeric"}}}
    delta = {"columns": {"b": {"type": "categorical"}}}
    merge_delta(acc, delta)
    assert acc == {"columns": {"a": {"type": "numeric"}}}
    assert delta == {"columns": {"b": {"type": "categorical"}}}


def test_inventaire_vide_le_dit() -> None:
    assert "aucune entrée" in inventory_line(None).lower()
    assert "aucune entrée" in inventory_line({}).lower()


def test_inventaire_compte_et_trie_les_noms() -> None:
    """L'inventaire donne le compte et des noms triés.

    Un ordre instable ferait varier le prompt d'un tour à l'autre sans raison.
    """
    acc = {"columns": {"zeta": {}, "alpha": {}, "mu": {}}}
    ligne = inventory_line(acc)
    assert "3" in ligne
    assert ligne.index("alpha") < ligne.index("mu") < ligne.index("zeta")
