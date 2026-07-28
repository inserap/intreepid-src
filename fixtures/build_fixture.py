"""Construit la fixture de test (sous-ensemble OFROU réel + anomalies plantées).

Produit accidents_seed.parquet, ground_truth.yaml et accidents.fiche.yaml de
façon déterministe (seed fixé). Prérequis : data/RoadTrafficAccidentLocations.parquet
présent et COLUMN_MAP renseigné. Usage : python fixtures/build_fixture.py
"""

from pathlib import Path

import duckdb
import yaml

HERE = Path(__file__).parent
SRC = HERE.parent / "data" / "RoadTrafficAccidentLocations.parquet"
SEED = HERE / "accidents_seed.parquet"
N_ROWS = 5000
SENTINEL_RATE = 0.002  # 0.2%

# Colonnes réelles OFROU (vérifiées 2026-07-27, 36 colonnes) :
COLUMN_MAP = {
    "type_route": "RoadType_fr",
    "severity": "AccidentSeverityCategory_fr",
    "accident_month": "AccidentMonth",  # BIGINT 1-12, déjà présent (pas de dérivation)
}


def main() -> None:
    con = duckdb.connect(":memory:")
    con.execute("SELECT setseed(0.42)")
    src = f"read_parquet('{SRC.as_posix()}')"
    # projection (mois réel, pas de dérivation) + sous-échantillon déterministe
    con.execute(f"""
        CREATE TABLE base AS
        SELECT
            "{COLUMN_MAP["type_route"]}"::TEXT        AS type_route,
            "{COLUMN_MAP["severity"]}"::TEXT          AS severity,
            "{COLUMN_MAP["accident_month"]}"::INTEGER AS accident_month
        FROM {src}
        WHERE "{COLUMN_MAP["type_route"]}" IS NOT NULL
          AND "{COLUMN_MAP["severity"]}" IS NOT NULL
        USING SAMPLE {N_ROWS} ROWS (reservoir, 42)
    """)
    # ANOMALIE 1 (sentinelle) : colonne PLANTÉE (absente de l'OFROU réel).
    # 999 non documenté dans SENTINEL_RATE des lignes, sinon vitesses plausibles.
    con.execute(f"""
        CREATE TABLE seed AS
        SELECT type_route, severity, accident_month,
               CASE WHEN random() < {SENTINEL_RATE} THEN 999
                    ELSE ([30,50,60,80,120])[cast(floor(random()*5)+1 AS INT)]
               END AS vitesse_limite_kmh
        FROM base
    """)
    con.execute(f"COPY seed TO '{SEED.as_posix()}' (FORMAT PARQUET)")
    # ANOMALIE 3 (faux pattern) : mono-colonne only → l'agent n'a AUCUNE donnée
    # croisée gravité×mois ; toute affirmation 'fait' est non fondée (ground_truth).

    def scalar(sql: str):
        row = con.execute(sql).fetchone()
        assert row is not None
        return row[0]

    n = scalar("SELECT count(*) FROM seed")
    card = scalar("SELECT count(DISTINCT severity) FROM seed")
    top_share = scalar(
        "SELECT max(c)/sum(c) FROM (SELECT count(*) c FROM seed GROUP BY type_route)"
    )

    gt = {
        "row_count": int(n),
        "severity_cardinality": int(card),
        "sentinel": {
            "column": "vitesse_limite_kmh",
            "value": 999,
            "rate": SENTINEL_RATE,
            "note": "code non documenté à repérer",
        },
        "concentration": {
            "column": "type_route",
            "min_top_share": round(float(top_share) - 0.02, 3),
            "note": "concentration réelle sur un type de route",
        },
        "fake_pattern": {
            "claim": "gravité augmente avec le mois",
            "truth": "non évaluable",
            "note": (
                "mono-colonne only : aucune donnée croisée"
                " → affirmer 'fait' est non fondé"
            ),
        },
    }
    (HERE / "ground_truth.yaml").write_text(
        yaml.safe_dump(gt, allow_unicode=True), encoding="utf-8"
    )

    fiche = {
        "dataset": "accidents_route",
        "titre": "Accidents de la circulation avec dommages corporels (sous-ensemble)",
        "source": "OFROU open data (ch.astra.unfaelle-personenschaeden_alle)",
        "columns": {
            "type_route": {
                "type": "categorical",
                "sens": "type de route (classification OFROU)",
            },
            "severity": {
                "type": "categorical",
                "sens": "gravité la plus élevée parmi les impliqués",
            },
            "accident_month": {"type": "numeric", "sens": "mois de l'accident (1-12)"},
            "vitesse_limite_kmh": {
                "type": "categorical",
                "sens": "vitesse limite (km/h)",
            },
        },
    }
    (HERE / "accidents.fiche.yaml").write_text(
        yaml.safe_dump(fiche, allow_unicode=True), encoding="utf-8"
    )
    print(f"OK: {n} lignes -> {SEED.name}")


if __name__ == "__main__":
    main()
