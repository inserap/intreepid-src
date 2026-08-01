"""Ingestion : population résidente par canton (exposition du modèle nul).

Source : OFS/BFS STATPOP, population résidente permanente (ordre de grandeur
2023 ; valeurs publiques, à rafraîchir). Sert de DÉNOMINATEUR (proxy grossier —
pas le trafic) au concentration_test sur `canton`. Sortie gitignorée, régénérable :
    uv run python -m prepare.canton_population
"""

from pathlib import Path

import duckdb

# Codes cantonaux officiels (CantonCode OFROU) → population résidente (approx.).
POPULATION: dict[str, int] = {
    "ZH": 1_579_000,
    "BE": 1_051_000,
    "VD": 826_000,
    "AG": 706_000,
    "SG": 521_000,
    "GE": 514_000,
    "LU": 424_000,
    "VS": 356_000,
    "TI": 351_000,
    "FR": 334_000,
    "BL": 292_000,
    "TG": 288_000,
    "SO": 281_000,
    "GR": 202_000,
    "BS": 196_000,
    "NE": 176_000,
    "SZ": 167_000,
    "ZG": 131_000,
    "SH": 84_000,
    "JU": 74_000,
    "AR": 55_800,
    "NW": 44_500,
    "GL": 41_000,
    "OW": 38_600,
    "UR": 37_300,
    "AI": 16_400,
}

HERE = Path(__file__).parent
OUT = HERE.parent / "data" / "prepared" / "canton_population.parquet"


def write_parquet(out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    values = ", ".join(f"('{c}', {p})" for c, p in POPULATION.items())
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE t(canton TEXT, population INTEGER)")
    con.execute(f"INSERT INTO t VALUES {values}")
    con.execute(f"COPY t TO '{out.as_posix()}' (FORMAT PARQUET)")
    con.close()


def main() -> None:
    write_parquet(OUT)
    print(f"OK: {len(POPULATION)} cantons -> {OUT}")


if __name__ == "__main__":
    main()
