"""Robustesse d'échelle spatiale — agnostique au domaine.

Agrège les points d'un dataset en cellules Uber H3 à plusieurs résolutions et
teste si une concentration (vs exposition déclarée) survit au changement de
maille. Reprojection SRID→WGS84 en SQL DuckDB ; null par redistribution
multinomiale ∝ exposition (réutilise nullmodel.pseudo_p). Le LLM ne reçoit que
des agrégats et des identifiants de cellule (P2) ; connexion read-only (P3).
Caveat assumé : agrégation planaire — biaisée pour un phénomène de réseau.
"""

from typing import Any

import duckdb
import h3


def spatial_col_of(fiche: dict[str, Any]) -> str:
    """Nom de la colonne spatiale ponctuelle déclarée dans la fiche."""
    for name, meta in fiche["columns"].items():
        if (
            meta.get("type") == "spatial"
            and meta.get("geometry_type_attendu") == "point"
        ):
            return name
    raise ValueError("aucune colonne spatiale ponctuelle dans la fiche")


def _ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"nom de colonne invalide: {name!r}")
    return f'"{name}"'


def h3_counts(
    con: duckdb.DuckDBPyConnection,
    table: str,
    geom_col: str,
    srid: int,
    resolution: int,
) -> dict[str, int]:
    """Reprojette les points en WGS84 et compte-les par cellule H3."""
    g, t = _ident(geom_col), _ident(table)
    # ST_Transform → WGS84 ; always_xy garantit (lng,lat) ; ST_X=lng, ST_Y=lat.
    src_srid = f"EPSG:{int(srid)}"
    sql = (
        f"SELECT ST_X(p) AS lng, ST_Y(p) AS lat FROM ("
        f"  SELECT ST_Transform({g}, '{src_srid}', 'EPSG:4326', always_xy := true)"
        f" AS p FROM {t} WHERE {g} IS NOT NULL) q"
    )
    rows = con.execute(sql).fetchall()
    counts: dict[str, int] = {}
    for lng, lat in rows:
        cell = h3.latlng_to_cell(float(lat), float(lng), resolution)
        counts[cell] = counts.get(cell, 0) + 1
    return counts
