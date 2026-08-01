"""Vérifie l'ingestion : table de population cantonale (exposition) bien formée."""

import duckdb

from prepare.canton_population import POPULATION, write_parquet


def test_population_covers_26_cantons_all_positive():
    assert len(POPULATION) == 26
    assert all(v > 0 for v in POPULATION.values())
    assert "BE" in POPULATION and "ZH" in POPULATION and "GE" in POPULATION


def test_write_parquet_roundtrip(tmp_path):
    out = tmp_path / "canton_population.parquet"
    write_parquet(out)
    con = duckdb.connect(":memory:")
    rows = con.execute(
        f"SELECT canton, population FROM read_parquet('{out.as_posix()}')"
    ).fetchall()
    assert len(rows) == 26
    assert all(p > 0 for _, p in rows)
