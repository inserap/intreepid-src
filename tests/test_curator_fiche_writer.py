"""Vérifie l'écriture de fiche : round-trip, hash stable, idempotence."""

import yaml

from intreepid.agent.curator.fiche_writer import (
    fiche_sha256,
    write_fiche,
    write_questions,
)
from intreepid.mcp_server.catalog import load_fiche

_DRAFT = {
    "dataset": "accidents_route",
    "titre": "Accidents (OFROU)",
    "columns": {
        "vitesse": {
            "type": "categorical",
            "sens": "vitesse",
            "piege": "999 = manquant",
        },
        "geom": {"type": "spatial", "srid": 2056, "unite": "mètres"},
    },
}


def test_write_roundtrips_through_load_fiche(tmp_path):
    path = tmp_path / "catalog" / "accidents_route.fiche.yaml"
    write_fiche(_DRAFT, path)
    assert load_fiche(path) == _DRAFT


def test_hash_is_stable_regardless_of_key_order():
    reordered = {
        "columns": _DRAFT["columns"],
        "titre": _DRAFT["titre"],
        "dataset": "accidents_route",
    }
    assert fiche_sha256(_DRAFT) == fiche_sha256(reordered)


def test_write_returns_hash_matching_helper(tmp_path):
    path = tmp_path / "f.fiche.yaml"
    assert write_fiche(_DRAFT, path) == fiche_sha256(_DRAFT)


def test_write_is_idempotent(tmp_path):
    path = tmp_path / "f.fiche.yaml"
    h1 = write_fiche(_DRAFT, path)
    mtime1 = path.stat().st_mtime_ns
    h2 = write_fiche(_DRAFT, path)  # même contenu => no-op
    assert h1 == h2
    assert path.stat().st_mtime_ns == mtime1  # fichier non réécrit


def test_write_questions_ecrit_du_yaml_relisible(tmp_path) -> None:
    path = tmp_path / "d.questions.yaml"
    h = write_questions([{"n": 1, "colonne": "a", "reponse": "1a"}], path)
    relu = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert relu[0]["n"] == 1
    assert relu[0]["reponse"] == "1a"
    assert len(h) == 64


def test_write_questions_est_idempotent(tmp_path) -> None:
    path = tmp_path / "d.questions.yaml"
    a = write_questions([{"n": 1}], path)
    mtime = path.stat().st_mtime_ns
    b = write_questions([{"n": 1}], path)
    assert a == b
    assert path.stat().st_mtime_ns == mtime  # contenu identique => no-op


def test_write_questions_naltere_pas_le_hash_de_la_fiche(tmp_path) -> None:
    """Garde I-G : le hash de validation porte sur la FICHE seule.

    Les deux artefacts sont écrits au même moment ; si un jour quelqu'un
    fusionnait les deux dumps, le hash cesserait d'être comparable aux séances
    passées (`ca40080edb96…` pour le gate du 06/08).
    """
    fiche = {"dataset": "d", "columns": {"a": {}}}
    avant = fiche_sha256(fiche)
    write_questions([{"n": 1}], tmp_path / "d.questions.yaml")
    assert fiche_sha256(fiche) == avant
