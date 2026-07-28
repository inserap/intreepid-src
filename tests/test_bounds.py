"""Vérifie la garantie read-only de la connexion DuckDB bornée (invariant P3).

Teste que la lecture est possible et que toute tentative d'écriture DDL/DML
lève une duckdb.Error comme attendu.
"""

import duckdb
import pytest

from intreepid.mcp_server.bounds import open_readonly
from tests.conftest import SEED_PARQUET, scalar


def test_readonly_can_read():
    con = open_readonly(SEED_PARQUET, "accidents_route")
    try:
        assert scalar(con, "SELECT count(*) FROM accidents_route") > 0
    finally:
        con.close()


def test_readonly_rejects_writes():
    con = open_readonly(SEED_PARQUET, "accidents_route")
    try:
        with pytest.raises(duckdb.Error):
            con.execute("CREATE TABLE t AS SELECT 1")
    finally:
        con.close()
