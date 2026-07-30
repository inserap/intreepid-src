"""Construit la fixture de test (sous-ensemble OFROU réel + anomalies plantées).

Produit accidents_seed.parquet, ground_truth.yaml et accidents.fiche.yaml de
façon déterministe (seed fixé). Prérequis : data/RoadTrafficAccidentLocations.parquet
présent et COLUMN_MAP renseigné. Usage : uv run python fixtures/build_fixture.py

Anomalies plantées : sentinelle 999 (vitesse), trou de série temporel + rupture de
volume (mois retirés), coordonnées implausibles (null-island (0,0) + hors emprise CH).
"""

from pathlib import Path

import duckdb
import yaml

HERE = Path(__file__).parent
SRC = HERE.parent / "data" / "RoadTrafficAccidentLocations.parquet"
SEED = HERE / "accidents_seed.parquet"
N_ROWS = 5000
SENTINEL_RATE = 0.002  # 0.2% pour la sentinelle vitesse 999
GEO_SENTINEL_RATE = (
    0.01  # taux nominal ~1% (le taux effectif réel est enregistré dans ground_truth)
)
GAP_YEARS = (
    2018,
    2019,
)  # années retirées -> trou de série + rupture de volume (≥2 éléments)

# Colonnes réelles OFROU (vérifiées 2026-07-27, 36 colonnes) :
COLUMN_MAP = {
    "type_route": "RoadType_fr",
    "severity": "AccidentSeverityCategory_fr",
    "accident_month": "AccidentMonth",  # BIGINT 1-12
    "year": "AccidentYear",
    "east": "AccidentLocation_CHLV95_E",
    "north": "AccidentLocation_CHLV95_N",
    "canton": "CantonCode",
}


def main() -> None:
    con = duckdb.connect(":memory:")
    con.execute("INSTALL spatial")
    con.execute("LOAD spatial")
    con.execute("SELECT setseed(0.42)")
    src = f"read_parquet('{SRC.as_posix()}')"
    m = COLUMN_MAP
    # construction explicite (évite (2018,))
    gap_list = ", ".join(str(y) for y in GAP_YEARS)
    # projection + sous-échantillon déterministe ; retire GAP_YEARS (trou/rupture)
    con.execute(f"""
        CREATE TABLE base AS
        SELECT
            "{m["type_route"]}"::TEXT        AS type_route,
            "{m["severity"]}"::TEXT          AS severity,
            "{m["accident_month"]}"::INTEGER AS accident_month,
            "{m["year"]}"::INTEGER           AS year,
            "{m["east"]}"::DOUBLE            AS east,
            "{m["north"]}"::DOUBLE           AS north,
            "{m["canton"]}"::TEXT            AS canton
        FROM {src}
        WHERE "{m["type_route"]}" IS NOT NULL
          AND "{m["severity"]}" IS NOT NULL
          AND "{m["year"]}" NOT IN ({gap_list})
        USING SAMPLE {N_ROWS} ROWS (reservoir, 42)
    """)
    # ANOMALIE 1 (sentinelle vitesse) + ANOMALIE 2 (date) + ANOMALIE spatiale.
    # ST_Point(north, east) : E/N inversés -> coordonnées hors emprise CH
    # Note : date est toujours fixée au 1er du mois (année + mois OFROU)
    con.execute(f"""
        CREATE TABLE seed AS
        SELECT type_route, severity, accident_month, canton,
               make_date(year, accident_month, 1) AS date,
               CASE WHEN random() < {SENTINEL_RATE} THEN 999
                    ELSE ([30,50,60,80,120])[cast(floor(random()*5)+1 AS INT)]
               END AS vitesse_limite_kmh,
               CASE
                   WHEN random() < {GEO_SENTINEL_RATE / 2} THEN ST_Point(0, 0)
                   WHEN random() < {GEO_SENTINEL_RATE} THEN ST_Point(north, east)
                   ELSE ST_Point(east, north)
               END AS geom
        FROM base
    """)
    con.execute(f"COPY seed TO '{SEED.as_posix()}' (FORMAT PARQUET)")
    # ANOMALIE (faux pattern) : mono-colonne only -> aucune donnée croisée
    # gravité×mois ET aucune preuve que la baisse de volume = routes plus sûres
    # (artefact de collecte).

    # M1 : calculer le ground_truth depuis le PARQUET RELU (pas la table en
    # mémoire), pour que build et tests lisent EXACTEMENT la même source
    # (round-trip GeoParquet inclus).
    rel = f"read_parquet('{SEED.as_posix()}')"

    def scalar(sql: str):
        row = con.execute(sql).fetchone()
        assert row is not None
        return row[0]

    n = scalar(f"SELECT count(*) FROM {rel}")
    card = scalar(f"SELECT count(DISTINCT severity) FROM {rel}")
    top_share = scalar(
        f"SELECT max(c)/sum(c) FROM (SELECT count(*) c FROM {rel} GROUP BY type_route)"
    )
    missing = scalar(f"""
        WITH b AS (
            SELECT date_trunc('month', min(date)) a,
                   date_trunc('month', max(date)) b
            FROM {rel}
        ),
        e AS (SELECT unnest(generate_series(a, b, INTERVAL 1 MONTH)) m FROM b),
        p AS (SELECT DISTINCT date_trunc('month', date) m FROM {rel})
        SELECT count(*) FROM e LEFT JOIN p USING(m) WHERE p.m IS NULL
    """)
    out_env = scalar(f"""
        SELECT count(*) FROM {rel} WHERE geom IS NOT NULL AND (
            (ST_XMin(geom)=0 AND ST_YMin(geom)=0)
            OR ST_XMin(geom) NOT BETWEEN 2480000 AND 2840000
            OR ST_YMin(geom) NOT BETWEEN 1070000 AND 1300000)
    """)

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
        "temporal_gap": {
            "column": "date",
            "missing_months": int(missing),
            "removed_years": list(GAP_YEARS),
            "note": (
                "années retirées -> trou de série + rupture de volume"
                " (changement de collecte)"
            ),
        },
        "spatial_sentinel": {
            "column": "geom",
            "rate": round(float(out_env) / float(n), 4),
            "note": "coordonnées implausibles : null-island (0,0) + hors emprise CH",
        },
        "fake_pattern": {
            "claim": "gravité augmente avec le mois",
            "truth": "non évaluable",
            "note": (
                "mono-colonne only : aucune donnée croisée"
                " -> affirmer 'fait' est non fondé"
            ),
        },
        "fake_temporal_pattern": {
            "claim": "la baisse de volume prouve que les routes deviennent plus sûres",
            "truth": "non fondé",
            "note": (
                "la baisse est un artefact de collecte (années retirées)"
                " ; causalité non établie"
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
            # `vitesse_limite_kmh` typée `categorical` À DESSEIN (commentaire DEV,
            # non exposé à l'agent) : le top-k fait ressortir la sentinelle 999 en
            # valeur discrète ; en `numeric` elle se diluerait dans les agrégats.
            # NE PAS ajouter de champ (`note`…) qui la spoilerait : `describe` renvoie
            # la fiche telle quelle, l'agent doit DÉCOUVRIR 999 seul (Q-0004).
            "vitesse_limite_kmh": {
                "type": "categorical",
                "sens": "vitesse limite (km/h)",
            },
            "date": {
                "type": "temporal",
                "sens": "date de l'accident (1er du mois : année + mois OFROU)",
            },
            "canton": {
                "type": "categorical",
                "sens": "canton de l'accident (code officiel)",
            },
            "geom": {
                "type": "spatial",
                "srid": 2056,
                "geometry_type_attendu": "point",
                "sens": "localisation de l'accident (point LV95)",
                "piege": (
                    "géolocalisation GPS depuis 2016, adresse avant"
                    " -> précision variable"
                ),
                "unite": "mètres",
            },
        },
    }
    (HERE / "accidents.fiche.yaml").write_text(
        yaml.safe_dump(fiche, allow_unicode=True), encoding="utf-8"
    )
    print(f"OK: {n} lignes -> {SEED.name} (trous={missing}, hors_emprise={out_env})")


if __name__ == "__main__":
    main()
