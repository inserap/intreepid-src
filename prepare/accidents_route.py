"""Ingestion : OFROU brut -> parquet analysis-ready (contrat vu par le MCP).

Projette/renomme les colonnes réelles vers le schéma de la fiche
catalog/accidents_route.fiche.yaml, construit geom (LV95, SRID 2056) et date
(1er du mois). AUCUNE anomalie plantée (c'est du réel). Sortie gitignorée,
régénérable :  uv run python -m prepare.accidents_route
Entrée : data/raw/RoadTrafficAccidentLocations.parquet — artefact raw fourni en
amont (conversion CSV->parquet = job ETL/FME, hors périmètre de notre solution).
Source OFROU : ch.astra.unfaelle-personenschaeden_alle (opendata.swiss).
"""

from pathlib import Path

import duckdb

HERE = Path(__file__).parent
SRC = HERE.parent / "data" / "raw" / "RoadTrafficAccidentLocations.parquet"
OUT = HERE.parent / "data" / "prepared" / "accidents_route.parquet"

COLUMN_MAP = {
    "type_route": "RoadType_fr",
    "severity": "AccidentSeverityCategory_fr",
    "accident_month": "AccidentMonth",
    "year": "AccidentYear",
    "east": "AccidentLocation_CHLV95_E",
    "north": "AccidentLocation_CHLV95_N",
    "canton": "CantonCode",
    "implique_pieton": "AccidentInvolvingPedestrian",
    "implique_velo": "AccidentInvolvingBicycle",
    "implique_moto": "AccidentInvolvingMotorcycle",
}


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    m = COLUMN_MAP
    con = duckdb.connect(":memory:")
    con.execute("INSTALL spatial")
    con.execute("LOAD spatial")
    src = f"read_parquet('{SRC.as_posix()}')"
    con.execute(f"""
        COPY (
            SELECT
                "{m["type_route"]}"::TEXT        AS type_route,
                "{m["severity"]}"::TEXT          AS severity,
                "{m["accident_month"]}"::INTEGER AS accident_month,
                "{m["canton"]}"::TEXT            AS canton,
                "{m["implique_pieton"]}"::TEXT   AS implique_pieton,
                "{m["implique_velo"]}"::TEXT     AS implique_velo,
                "{m["implique_moto"]}"::TEXT     AS implique_moto,
                make_date(
                    "{m["year"]}"::INTEGER, "{m["accident_month"]}"::INTEGER, 1
                ) AS date,
                ST_Point("{m["east"]}"::DOUBLE, "{m["north"]}"::DOUBLE) AS geom
            FROM {src}
            WHERE "{m["type_route"]}" IS NOT NULL
              AND "{m["severity"]}" IS NOT NULL
              AND "{m["canton"]}" IS NOT NULL
        ) TO '{OUT.as_posix()}' (FORMAT PARQUET)
    """)
    n = con.execute(f"SELECT count(*) FROM read_parquet('{OUT.as_posix()}')").fetchone()
    con.close()
    print(f"OK: {n[0] if n else 0} lignes -> {OUT}")


if __name__ == "__main__":
    main()
