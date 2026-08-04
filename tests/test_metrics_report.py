"""Couverture du CLI metrics_report (intreepid/metrics_report.py).

Branches testées :
- fichier absent → SystemExit avec message lisible
- plusieurs sessions → SystemExit avec liste des sessions
- session_id inconnu → SystemExit (message humain, pas de trace Python brute)
- session unique → sortie normale avec rendu

Toutes les traces sont construites avec Scribe + record_nodes (aucun appel LLM).
"""

import sys

import pytest

from intreepid.metrics_report import main
from intreepid.scribe.store import Scribe


def _db_une_session(tmp_path, sid="sess1"):
    """Crée un .duckdb avec une session minimaliste (aucun appel LLM)."""
    db = tmp_path / f"{sid}.duckdb"
    with Scribe(db, sid, "question test", "opus") as sc:
        sc.record_nodes(
            [("observation", {"claim": "test", "note": None}, {"statut": "fait"})]
        )
    return db


def test_fichier_absent_leve_systemexit(tmp_path, monkeypatch):
    absent = tmp_path / "inexistant.duckdb"
    monkeypatch.setattr(sys, "argv", ["metrics_report", str(absent)])
    with pytest.raises(SystemExit) as exc:
        main()
    assert "introuvable" in str(exc.value).lower()


def test_plusieurs_sessions_leve_systemexit(tmp_path, monkeypatch):
    db = tmp_path / "multi.duckdb"
    # Deux sessions dans le même fichier
    with Scribe(db, "sess_a", "question A", "opus") as sc:
        sc.record_nodes([("observation", {"claim": "A"}, {})])
    with Scribe(db, "sess_b", "question B", "opus") as sc:
        sc.record_nodes([("observation", {"claim": "B"}, {})])
    monkeypatch.setattr(sys, "argv", ["metrics_report", str(db)])
    with pytest.raises(SystemExit) as exc:
        main()
    msg = str(exc.value)
    assert "sessions" in msg.lower()
    assert "sess_a" in msg
    assert "sess_b" in msg


def test_session_id_inconnu_leve_systemexit(tmp_path, monkeypatch):
    db = _db_une_session(tmp_path, "sess1")
    monkeypatch.setattr(sys, "argv", ["metrics_report", str(db), "id_fantome"])
    with pytest.raises(SystemExit) as exc:
        main()
    msg = str(exc.value)
    assert "introuvable" in msg.lower()
    # Le message doit être lisible, pas une trace Python brute
    assert "KeyError" not in msg
    assert "Traceback" not in msg


def test_session_unique_sortie_normale(tmp_path, monkeypatch, capsys):
    db = _db_une_session(tmp_path, "sess1")
    monkeypatch.setattr(sys, "argv", ["metrics_report", str(db)])
    main()  # ne doit pas lever
    out = capsys.readouterr().out
    assert "sess1" in out
    assert "Session" in out
