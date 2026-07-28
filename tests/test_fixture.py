"""Vérifie que la fixture porte bien les vérités plantées (ground truth).

Contrôle la présence de la sentinelle 999, la cardinalité de gravité et la
concentration sur type_route conformément au manifeste ground_truth.yaml.
"""

import duckdb
import yaml

from tests.conftest import GROUND_TRUTH, SEED_PARQUET, scalar


def test_fixture_planted_truths():
    assert SEED_PARQUET.exists(), "lance d'abord: python fixtures/build_fixture.py"
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
