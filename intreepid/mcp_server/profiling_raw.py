"""Profil brut d'un dataset SANS fiche — inférence de type (Q-0015a, ingestion).

Profiler un parquet non encore fiché : lit le schéma DuckDB, infère un TYPE
CANDIDAT par colonne (le curateur/l'humain valide — jamais une vérité), et
réutilise les profileurs de ``profile_stats`` (qui ne dépendent que de
``con+table+col``). Agrégats only (P2), read-only (P3). **Table non vide
supposée** : un profileur sur table vide divise par ``n=0`` — l'outil MCP garde
``is_file`` en amont, l'ingestion d'une table vide est hors périmètre #7b.
"""

from typing import Any

import duckdb

from intreepid.mcp_server.profile_stats import (
    _categorical,
    _ident,
    _numeric,
    _spatial,
    _temporal,
)

CARD_CATEGORICAL_MAX = 25  # numérique sous ce seuil = probablement un code déguisé


def _schema(con: duckdb.DuckDBPyConnection, table: str) -> list[tuple[str, str]]:
    """Liste (colonne, type SQL DuckDB majuscule) via UN SEUL DESCRIBE (évite O(n²))."""
    rows = con.execute(f"DESCRIBE {_ident(table)}").fetchall()
    # DESCRIBE → (column_name, column_type, null, key, default, extra)
    return [(r[0], str(r[1]).upper()) for r in rows]


def _infer_from_sql_type(
    con: duckdb.DuckDBPyConnection, table: str, col: str, sql_type: str
) -> str:
    if "GEOMETRY" in sql_type:
        return "spatial"
    if sql_type.startswith(("DATE", "TIMESTAMP", "TIME")):
        return "temporal"
    numeric = any(
        k in sql_type for k in ("INT", "DOUBLE", "FLOAT", "DECIMAL", "REAL", "HUGEINT")
    )
    if numeric:
        c, t = _ident(col), _ident(table)
        card = con.execute(f"SELECT count(DISTINCT {c}) FROM {t}").fetchone()
        if card is not None and card[0] is not None and card[0] <= CARD_CATEGORICAL_MAX:
            return "categorical"  # code déguisé (faible cardinalité)
        return "numeric"
    return "categorical"  # VARCHAR / BOOLEAN / autres


def infer_type(con: duckdb.DuckDBPyConnection, table: str, col: str) -> str:
    """Infère un type candidat (categorical/numeric/temporal/spatial) sans fiche."""
    for name, sql_type in _schema(con, table):
        if name == col:
            return _infer_from_sql_type(con, table, col, sql_type)
    raise ValueError(f"colonne absente du schéma: {col!r}")


def profile_raw(
    con: duckdb.DuckDBPyConnection, table: str
) -> dict[str, dict[str, Any]]:
    """Profile toutes les colonnes d'un dataset non-fiché ; types inférés marqués."""
    out: dict[str, dict[str, Any]] = {}
    for col, sql_type in _schema(con, table):  # un seul DESCRIBE partagé
        t = _infer_from_sql_type(con, table, col, sql_type)
        if t == "categorical":
            prof = _categorical(con, table, col)
        elif t == "numeric":
            prof = _numeric(con, table, col)
        elif t == "temporal":
            prof = _temporal(con, table, col)
        else:
            prof = _spatial(con, table, col, {})  # pas de fiche → srid_declared=None
        out[col] = {**prof, "type_inferred": True}
    return out
