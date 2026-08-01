"""Ingestion : BFS STATPOP 2024 brut -> parquet analysis-ready (contrat vu par le MCP).

Projette les colonnes spatiales (E_KOORD, N_KOORD en LV95 EPSG:2056) et la
population par hectare (BBTOT). Pas d'extension spatiale nécessaire : projection
de colonnes pure, pas de ST_*.
Source BFS GEOSTAT : bevolkerungsstatistik-einwohner (opendata.swiss).
k-anonymat déjà appliqué en amont par le BFS (comptages ≤ 2 supprimés).
Sortie gitignorée, régénérable : uv run python -m prepare.statpop_population
Entrée : data/raw/STATPOP2024.parquet — artefact raw fourni en amont (conversion
CSV->parquet = job ETL/FME, hors périmètre de notre solution).
"""

from pathlib import Path

import duckdb

HERE = Path(__file__).parent
SRC = HERE.parent / "data" / "raw" / "STATPOP2024.parquet"
OUT = HERE.parent / "data" / "prepared" / "statpop_population.parquet"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(":memory:")
    con.execute(f"""
        COPY (
            SELECT
                "E_KOORD"::DOUBLE  AS east,
                "N_KOORD"::DOUBLE  AS north,
                "BBTOT"::INTEGER   AS population
            FROM read_parquet('{SRC.as_posix()}')
            WHERE "BBTOT" > 0
        ) TO '{OUT.as_posix()}' (FORMAT PARQUET)
    """)
    n = con.execute(f"SELECT count(*) FROM read_parquet('{OUT.as_posix()}')").fetchone()
    con.close()
    print(f"OK: {n[0] if n else 0} lignes -> {OUT}")


if __name__ == "__main__":
    main()
