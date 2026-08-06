"""Vérifie que la fin de séance du curateur ne se tait jamais (gate humain)."""

import duckdb

from intreepid.demo_curator import _preuve_et_mesures
from intreepid.scribe.store import Scribe


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
