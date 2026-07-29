"""Vérifie la garantie read-only de la connexion DuckDB bornée (invariant P3).

Teste que la lecture est possible, que toute écriture DDL/DML lève une
duckdb.Error, et que le dossier temporaire est nettoyé en sortie (pas de fuite).
"""

from pathlib import Path

import duckdb
import pytest

from intreepid.mcp_server.bounds import open_readonly
from tests.conftest import SEED_PARQUET, scalar


def test_readonly_can_read():
    with open_readonly(SEED_PARQUET, "accidents_route") as con:
        assert scalar(con, "SELECT count(*) FROM accidents_route") > 0


def test_readonly_rejects_writes():
    with open_readonly(SEED_PARQUET, "accidents_route") as con:
        with pytest.raises(duckdb.Error):
            con.execute("CREATE TABLE t AS SELECT 1")


def test_spatial_extension_loaded():
    with open_readonly(SEED_PARQUET, "accidents_route") as con:
        # ST_Point n'est résolu que si l'extension spatial est chargée
        row = con.execute("SELECT ST_AsText(ST_Point(2600000, 1200000))").fetchone()
        assert row is not None and "POINT" in row[0]


def test_tempdir_cleaned_on_exit():
    seen: list[Path] = []
    with open_readonly(SEED_PARQUET, "accidents_route") as con:
        # localise le fichier .duckdb ouvert via le catalogue DuckDB
        row = con.execute("PRAGMA database_list").fetchall()
        dbpath = Path([r for r in row if r[1] != "system"][0][2])
        seen.append(dbpath)
        assert dbpath.exists()
    assert not seen[0].exists(), "le dossier temporaire doit être nettoyé en sortie"
