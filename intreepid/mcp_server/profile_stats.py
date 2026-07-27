TOP_K = 15  # cap dur (borne)

def _ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"nom de colonne invalide: {name!r}")
    return f'"{name}"'

def _categorical(con, table, col) -> dict:
    c, t = _ident(col), _ident(table)
    n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    card = con.execute(f"SELECT count(DISTINCT {c}) FROM {t}").fetchone()[0]
    rows = con.execute(
        f"SELECT {c} AS v, count(*) AS f FROM {t} GROUP BY {c} ORDER BY f DESC LIMIT {TOP_K}"
    ).fetchall()
    top_k = [{"value": r[0], "freq": round(r[1] / n, 4)} for r in rows]
    entropy = con.execute(
        f"SELECT -sum(p*log2(p)) FROM (SELECT count(*)::double/{n} p FROM {t} GROUP BY {c})"
    ).fetchone()[0]
    return {"type": "categorical", "n": n, "cardinality": card,
            "uniqueness": round(card / n, 4), "entropy": round(entropy or 0.0, 4),
            "top_k": top_k}

def _numeric(con, table, col) -> dict:
    c, t = _ident(col), _ident(table)
    n, nn, mn, mx, avg, med, p5, p25, p75, p95, std, zeros = con.execute(f"""
        SELECT count(*), count({c}), min({c}), max({c}), avg({c}), median({c}),
               quantile_cont({c},0.05), quantile_cont({c},0.25),
               quantile_cont({c},0.75), quantile_cont({c},0.95),
               stddev_samp({c}), sum(CASE WHEN {c}=0 THEN 1 ELSE 0 END)
        FROM {t}
    """).fetchone()
    outliers = 0
    if std and std > 0:
        outliers = con.execute(
            f"SELECT count(*) FROM {t} WHERE abs({c}-{avg}) > 3*{std}"
        ).fetchone()[0]
    return {"type": "numeric", "n": n, "min": mn, "max": mx,
            "mean": round(avg, 4), "median": med, "p5": p5, "p25": p25,
            "p75": p75, "p95": p95, "std": round(std or 0.0, 4),
            "null_rate": round((n - nn) / n, 4),
            "zero_rate": round(zeros / n, 4), "n_outliers_3sigma": outliers}

_DISPATCH = {"categorical": _categorical, "numeric": _numeric}

def profile_stats(con, table: str, fiche: dict, columns: list[str] | None = None) -> dict:
    allowed = fiche["columns"]
    cols = columns or list(allowed)
    out = {}
    for col in cols:
        if col not in allowed:
            raise ValueError(f"colonne hors allowlist de la fiche: {col!r}")
        ctype = allowed[col].get("type", "categorical")
        fn = _DISPATCH.get(ctype)
        if fn is None:
            raise ValueError(f"type de colonne non supporté dans la brique #1: {ctype!r}")
        out[col] = fn(con, table, col)
    return out
