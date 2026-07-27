import duckdb, pytest
from tests.conftest import SEED_PARQUET
from intreepid.mcp_server.bounds import open_readonly

def test_readonly_can_read():
    con = open_readonly(SEED_PARQUET, "accidents_route")
    try:
        assert con.execute("SELECT count(*) FROM accidents_route").fetchone()[0] > 0
    finally:
        con.close()

def test_readonly_rejects_writes():
    con = open_readonly(SEED_PARQUET, "accidents_route")
    try:
        with pytest.raises(duckdb.Error):
            con.execute("CREATE TABLE t AS SELECT 1")
    finally:
        con.close()
