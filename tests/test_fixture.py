"""Vérifie que la fixture porte bien les vérités plantées (ground truth).

Contrôle la présence de la sentinelle 999, la cardinalité de gravité, la
concentration sur type_route, le trou de série temporel et la sentinelle
spatiale, conformément au manifeste ground_truth.yaml.
"""

import duckdb
import yaml

from tests.conftest import GROUND_TRUTH, SEED_PARQUET, scalar


def test_fixture_planted_truths():
    assert SEED_PARQUET.exists(), (
        "lance d'abord: uv run python fixtures/build_fixture.py"
    )
    gt = yaml.safe_load(GROUND_TRUTH.read_text(encoding="utf-8"))
    con = duckdb.connect(":memory:")
    rel = f"read_parquet('{SEED_PARQUET.as_posix()}')"

    n = scalar(con, f"SELECT count(*) FROM {rel}")
    assert n == gt["row_count"]

    # sentinelle plantée
    s999 = scalar(con, f"SELECT count(*) FROM {rel} WHERE vitesse_limite_kmh = 999")
    assert abs(s999 / n - gt["sentinel"]["rate"]) < 0.001

    # cardinalité gravité
    card = scalar(con, f"SELECT count(DISTINCT severity) FROM {rel}")
    assert card == gt["severity_cardinality"]

    # vraie concentration : part de la 1re catégorie de type_route
    top_share = scalar(
        con,
        f"SELECT max(c)/sum(c) FROM (SELECT count(*) c FROM {rel} GROUP BY type_route)",
    )
    assert top_share >= gt["concentration"]["min_top_share"]

    # colonnes brique #2 présentes
    cols = {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {rel}").fetchall()}
    assert {"date", "geom", "canton"} <= cols

    # trou de série temporel planté (mois manquants > 0)
    con.execute("INSTALL spatial")
    con.execute("LOAD spatial")
    gaps = scalar(
        con,
        f"""
        WITH b AS (
            SELECT date_trunc('month', min(date)) a,
                   date_trunc('month', max(date)) b
            FROM {rel}
        ),
        e AS (SELECT unnest(generate_series(a, b, INTERVAL 1 MONTH)) m FROM b),
        p AS (SELECT DISTINCT date_trunc('month', date) m FROM {rel})
        SELECT count(*) FROM e LEFT JOIN p USING(m) WHERE p.m IS NULL
        """,
    )
    assert gaps == gt["temporal_gap"]["missing_months"]
    assert gaps > 0

    # sentinelle spatiale : géométries hors emprise CH (null-island + hors-CH)
    out_env = scalar(
        con,
        f"""
        SELECT count(*) FROM {rel} WHERE geom IS NOT NULL AND (
            (ST_XMin(geom)=0 AND ST_YMin(geom)=0)
            OR ST_XMin(geom) NOT BETWEEN 2480000 AND 2840000
            OR ST_YMin(geom) NOT BETWEEN 1070000 AND 1300000)
        """,
    )
    assert out_env > 0
    assert abs(out_env / n - gt["spatial_sentinel"]["rate"]) < 0.002


def test_exposure_table_and_hotspots():
    from intreepid.mcp_server.catalog import load_fiche  # noqa: PLC0415
    from tests.conftest import FICHE  # noqa: PLC0415

    expo = SEED_PARQUET.parent / "canton_exposure.parquet"
    assert expo.exists(), "lance d'abord: uv run python fixtures/build_fixture.py"

    gt = yaml.safe_load(GROUND_TRUTH.read_text(encoding="utf-8"))
    hs = gt["hotspot"]
    a, b = hs["true_hotspot"], hs["false_hotspot"]
    assert a != b

    con = duckdb.connect(":memory:")
    rel = f"read_parquet('{SEED_PARQUET.as_posix()}')"
    erel = f"read_parquet('{expo.as_posix()}')"

    # le faux point chaud = l'unité au plus gros comptage brut
    top_unit = scalar(
        con,
        f"SELECT canton FROM {rel} GROUP BY canton ORDER BY count(*) DESC LIMIT 1",
    )
    assert b == top_unit

    # l'exposition du vrai point chaud est RÉDUITE sous son comptage (excès réel)
    o_a = scalar(con, f"SELECT count(*) FROM {rel} WHERE canton = '{a}'")
    w_a = scalar(con, f"SELECT exposure FROM {erel} WHERE canton = '{a}'")
    assert w_a < o_a

    # toutes les unités des données ont une exposition déclarée
    missing = scalar(
        con,
        f"SELECT count(*) FROM (SELECT DISTINCT canton FROM {rel}) d"
        f" LEFT JOIN {erel} e USING (canton) WHERE e.canton IS NULL",
    )
    assert missing == 0

    # la fiche déclare la convention exposures
    fiche = load_fiche(FICHE)
    assert fiche["exposures"]["canton"]["table"] == "canton_exposure.parquet"
    assert fiche["exposures"]["canton"]["weight"] == "exposure"
