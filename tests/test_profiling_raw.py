"""Vérifie l'inférence de type brute (sans fiche) et le profil réutilisé."""

from pathlib import Path

import duckdb

from intreepid.mcp_server.bounds import open_readonly
from intreepid.mcp_server.profiling_raw import infer_type, profile_raw


def _synthetic_parquet(tmp_path: Path) -> Path:
    """Parquet contrôlé : id continu (card 50), code (card 3), label str, when date."""
    p = tmp_path / "raw.parquet"
    con = duckdb.connect()
    con.execute(
        f"""COPY (
            SELECT i::INTEGER AS id, (i % 3)::INTEGER AS code, 'x' || (i % 4) AS label,
                   DATE '2020-01-01' + (i::INTEGER) AS when_
            FROM range(50) t(i)
        ) TO '{p.as_posix()}' (FORMAT parquet)"""
    )
    con.close()
    return p


def test_infer_type_distinguishes_continuous_from_code(tmp_path):
    p = _synthetic_parquet(tmp_path)
    with open_readonly(p, "raw") as con:
        assert infer_type(con, "raw", "id") == "numeric"  # card 50 > seuil
        assert infer_type(con, "raw", "code") == "categorical"  # card 3 = code déguisé
        assert infer_type(con, "raw", "label") == "categorical"  # VARCHAR
        assert infer_type(con, "raw", "when_") == "temporal"  # DATE


def test_profile_raw_covers_all_columns_and_marks_inferred(tmp_path):
    p = _synthetic_parquet(tmp_path)
    with open_readonly(p, "raw") as con:
        prof = profile_raw(con, "raw")
    assert set(prof) == {"id", "code", "label", "when_"}
    assert prof["id"]["type"] == "numeric"
    assert prof["code"]["type"] == "categorical"
    assert prof["when_"]["type"] == "temporal"
    assert all(c["type_inferred"] is True for c in prof.values())


def test_profile_raw_infers_spatial_on_real_fixture():
    """Fixture réelle (a une geom + un code déguisé 999) : spatial + categorical."""
    fixture = Path(__file__).parent.parent / "fixtures" / "accidents_seed.parquet"
    with open_readonly(fixture, "accidents_seed") as con:
        assert infer_type(con, "accidents_seed", "geom") == "spatial"
        prof = profile_raw(con, "accidents_seed")
    assert prof["geom"]["type"] == "spatial"
    assert prof["vitesse_limite_kmh"]["type"] == "categorical"  # 999 + 5 modalités
