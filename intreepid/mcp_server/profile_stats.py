"""Carte d'identité statistique mono-colonne — proxy read-only des données.

Expose uniquement des agrégats (distribution, entropie, top-k) ; jamais de
lignes brutes au LLM (invariant P2 : pseudonymisation en amont via FME).
"""

from typing import Any

import duckdb

TOP_K = 15  # cap dur (borne)

# Emprise LV95 (EPSG:2056) approximative de la Suisse : E_min,E_max,N_min,N_max.
CH_BBOX = (2_480_000, 2_840_000, 1_070_000, 1_300_000)
_DEFERRED = "prévu / non implémenté (brique ultérieure : H3 multi-résolution anti-MAUP)"


def _ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"nom de colonne invalide: {name!r}")
    return f'"{name}"'


def _scalar(con: duckdb.DuckDBPyConnection, sql: str) -> Any:
    """Exécute une requête agrégat et retourne la 1re colonne de l'unique ligne."""
    row = con.execute(sql).fetchone()
    if row is None:
        raise RuntimeError(f"requête agrégat sans résultat : {sql}")
    return row[0]


def _categorical(
    con: duckdb.DuckDBPyConnection, table: str, col: str
) -> dict[str, Any]:
    c, t = _ident(col), _ident(table)
    n = _scalar(con, f"SELECT count(*) FROM {t}")
    card = _scalar(con, f"SELECT count(DISTINCT {c}) FROM {t}")
    rows = con.execute(
        f"SELECT {c} AS v, count(*) AS f FROM {t}"
        f" GROUP BY {c} ORDER BY f DESC LIMIT {TOP_K}"
    ).fetchall()
    top_k = [{"value": r[0], "freq": round(r[1] / n, 4)} for r in rows]
    entropy = _scalar(
        con,
        f"SELECT -sum(p*log2(p))"
        f" FROM (SELECT count(*)::double/{n} p FROM {t} GROUP BY {c})",
    )
    return {
        "type": "categorical",
        "n": n,
        "cardinality": card,
        "uniqueness": round(card / n, 4),
        "entropy": round(entropy or 0.0, 4),
        "top_k": top_k,
    }


def _numeric(con: duckdb.DuckDBPyConnection, table: str, col: str) -> dict[str, Any]:
    c, t = _ident(col), _ident(table)
    row = con.execute(f"""
        SELECT count(*), count({c}), min({c}), max({c}), avg({c}), median({c}),
               quantile_cont({c},0.05), quantile_cont({c},0.25),
               quantile_cont({c},0.75), quantile_cont({c},0.95),
               stddev_samp({c}), sum(CASE WHEN {c}=0 THEN 1 ELSE 0 END),
               skewness({c})
        FROM {t}
    """).fetchone()
    if row is None:
        raise RuntimeError(f"profil numérique sans résultat pour {col!r}")
    n, nn, mn, mx, avg, med, p5, p25, p75, p95, std, zeros, skew = row
    outliers = 0
    if std and std > 0:
        outliers = _scalar(
            con, f"SELECT count(*) FROM {t} WHERE abs({c}-{avg}) > 3*{std}"
        )
    return {
        "type": "numeric",
        "n": n,
        "min": mn,
        "max": mx,
        "mean": round(avg, 4),
        "median": med,
        "p5": p5,
        "p25": p25,
        "p75": p75,
        "p95": p95,
        "std": round(std or 0.0, 4),
        "skewness": round(skew or 0.0, 4),
        "null_rate": round((n - nn) / n, 4),
        "zero_rate": round(zeros / n, 4),
        "n_outliers_3sigma": outliers,
    }


def _temporal(con: duckdb.DuckDBPyConnection, table: str, col: str) -> dict[str, Any]:
    c, t = _ident(col), _ident(table)
    row = con.execute(
        f"SELECT count(*), count({c}), min({c}), max({c}) FROM {t}"
    ).fetchone()
    if row is None:
        raise RuntimeError(f"profil temporel sans résultat pour {col!r}")
    n, nn, mn, mx = row
    gaps = _scalar(
        con,
        f"""
        WITH bornes AS (
            SELECT date_trunc('month', min({c})) a,
                   date_trunc('month', max({c})) b
            FROM {t}
        ),
        expected AS (
            SELECT unnest(generate_series(a, b, INTERVAL 1 MONTH)) m
            FROM bornes
        ),
        present AS (
            SELECT DISTINCT date_trunc('month', {c}) m
            FROM {t} WHERE {c} IS NOT NULL
        )
        SELECT count(*) FROM expected e LEFT JOIN present p USING (m)
        WHERE p.m IS NULL
        """,
    )
    season = con.execute(
        f"SELECT month({c}) mo, count(*) f"
        f" FROM {t} WHERE {c} IS NOT NULL"
        f" GROUP BY mo ORDER BY mo"
    ).fetchall()
    volume = con.execute(
        f"SELECT year({c}) y, count(*) f"
        f" FROM {t} WHERE {c} IS NOT NULL"
        f" GROUP BY y ORDER BY y"
    ).fetchall()
    return {
        "type": "temporal",
        "n": n,
        "null_rate": round((n - nn) / n, 4),
        "min": str(mn),
        "max": str(mx),
        "series_gaps_months": gaps,
        # clés en str : cohérence direct↔MCP (FastMCP sérialise les clés JSON en str)
        "seasonality_by_month": {str(int(r[0])): r[1] for r in season},
        "volume_by_year": {str(int(r[0])): r[1] for r in volume},
    }


def _spatial(
    con: duckdb.DuckDBPyConnection, table: str, col: str, spec: dict[str, Any]
) -> dict[str, Any]:
    c, t = _ident(col), _ident(table)
    emin, emax, nmin, nmax = CH_BBOX
    row = con.execute(f"""
        SELECT count(*),
               count(*) FILTER (WHERE {c} IS NULL),
               count(*) FILTER (WHERE {c} IS NOT NULL AND ST_IsEmpty({c})),
               count(*) FILTER (WHERE {c} IS NOT NULL AND NOT ST_IsValid({c})),
               count(*) FILTER (WHERE {c} IS NOT NULL AND ST_HasZ({c})),
               count(*) FILTER (WHERE {c} IS NOT NULL AND (
                   (ST_XMin({c})=0 AND ST_YMin({c})=0)
                   OR ST_XMin({c}) NOT BETWEEN {emin} AND {emax}
                   OR ST_YMin({c}) NOT BETWEEN {nmin} AND {nmax}))
        FROM {t}
    """).fetchone()
    if row is None:
        raise RuntimeError(f"profil spatial sans résultat pour {col!r}")
    n, nulls, empties, invalids, zs, out_env = row
    types = {
        r[0]: r[1]
        for r in con.execute(
            f"SELECT ST_GeometryType({c}) g, count(*) f FROM {t}"
            f" WHERE {c} IS NOT NULL GROUP BY g ORDER BY f DESC"
        ).fetchall()
    }
    ext = con.execute(
        f"SELECT min(ST_XMin({c})), max(ST_XMax({c})),"
        f"       min(ST_YMin({c})), max(ST_YMax({c}))"
        f" FROM {t}"
        f" WHERE {c} IS NOT NULL AND NOT (ST_XMin({c})=0 AND ST_YMin({c})=0)"
        f"   AND ST_XMin({c}) BETWEEN {emin} AND {emax}"
        f"   AND ST_YMin({c}) BETWEEN {nmin} AND {nmax}"
    ).fetchone()
    if ext is None:
        raise RuntimeError(f"emprise spatiale sans résultat pour {col!r}")
    size = con.execute(
        f"SELECT max(ST_Length({c})), max(ST_Area({c})) FROM {t} WHERE {c} IS NOT NULL"
    ).fetchone()
    if size is None:
        raise RuntimeError(f"mesures de taille spatiale sans résultat pour {col!r}")
    return {
        "type": "spatial",
        "n": n,
        "srid_declared": spec.get("srid"),
        "geometry_types": types,
        "null_rate": round(nulls / n, 4),
        "empty_rate": round(empties / n, 4),
        "invalid_rate": round(invalids / n, 4),
        "has_z_rate": round(zs / n, 4),
        "out_of_envelope_rate": round(out_env / n, 4),
        "extent": {
            "min_x": ext[0],
            "max_x": ext[1],
            "min_y": ext[2],
            "max_y": ext[3],
        },
        "max_length": size[0],
        "max_area": size[1],
        "nearest_neighbor": _DEFERRED,
        "density_by_cell": _DEFERRED,
    }


_DISPATCH = {
    "categorical": _categorical,
    "numeric": _numeric,
    "temporal": _temporal,
    "spatial": _spatial,
}


def profile_stats(
    con: duckdb.DuckDBPyConnection,
    table: str,
    fiche: dict[str, Any],
    columns: list[str] | None = None,
) -> dict[str, Any]:
    allowed = fiche["columns"]
    cols = columns or list(allowed)
    out = {}
    for col in cols:
        if col not in allowed:
            raise ValueError(f"colonne hors allowlist de la fiche: {col!r}")
        spec = allowed[col]
        ctype = spec.get("type", "categorical")
        fn = _DISPATCH.get(ctype)
        if fn is None:
            raise ValueError(
                f"type de colonne prévu / non implémenté: {ctype!r}"
                " (types couverts: categorical, numeric, temporal, spatial)"
            )
        if ctype == "spatial":
            out[col] = fn(con, table, col, spec)
        else:
            out[col] = fn(con, table, col)
    return out
