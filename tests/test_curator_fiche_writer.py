"""Vérifie l'écriture de fiche : round-trip, hash stable, idempotence."""

from intreepid.agent.curator.fiche_writer import fiche_sha256, write_fiche
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
