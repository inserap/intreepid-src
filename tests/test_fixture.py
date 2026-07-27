import duckdb, yaml
from tests.conftest import SEED_PARQUET, GROUND_TRUTH

def test_fixture_planted_truths():
    assert SEED_PARQUET.exists(), "lance d'abord: python fixtures/build_fixture.py"
    gt = yaml.safe_load(GROUND_TRUTH.read_text(encoding="utf-8"))
    con = duckdb.connect(":memory:")
    rel = f"read_parquet('{SEED_PARQUET.as_posix()}')"

    n = con.execute(f"SELECT count(*) FROM {rel}").fetchone()[0]
    assert n == gt["row_count"]

    # sentinelle plantée
    s999 = con.execute(
        f"SELECT count(*) FROM {rel} WHERE vitesse_limite_kmh = 999"
    ).fetchone()[0]
    assert abs(s999 / n - gt["sentinel"]["rate"]) < 0.001

    # cardinalité gravité
    card = con.execute(
        f"SELECT count(DISTINCT severity) FROM {rel}"
    ).fetchone()[0]
    assert card == gt["severity_cardinality"]

    # vraie concentration : part de la 1re catégorie de type_route
    top_share = con.execute(
        f"SELECT max(c)/sum(c) FROM (SELECT count(*) c FROM {rel} GROUP BY type_route)"
    ).fetchone()[0]
    assert top_share >= gt["concentration"]["min_top_share"]
