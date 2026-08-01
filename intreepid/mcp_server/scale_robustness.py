"""Robustesse d'échelle spatiale — agnostique au domaine.

Agrège les points d'un dataset en cellules Uber H3 à plusieurs résolutions et
teste si une concentration (vs exposition déclarée) survit au changement de
maille. Reprojection SRID→WGS84 en SQL DuckDB ; null par redistribution
multinomiale ∝ exposition (réutilise nullmodel.pseudo_p). Le LLM ne reçoit que
des agrégats et des identifiants de cellule (P2) ; connexion read-only (P3).
Caveat assumé : agrégation planaire — biaisée pour un phénomène de réseau.
"""

from pathlib import Path
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


def h3_exposure(
    con: duckdb.DuckDBPyConnection,
    grid_fiche: dict[str, Any],
    base_dir: "str | Path",
    resolution: int,
    weight_col: str,
) -> dict[str, float]:
    """Agrège une grille de population (points-mailles) en cellules H3.

    `weight_col` est fourni par le lien d'exposition (`exposures.<col>.weight`),
    jamais inféré : le consommateur choisit la colonne de poids.
    """
    grid = grid_fiche["grid"]
    data = (Path(base_dir) / grid_fiche["data"]).as_posix()
    e_col, n_col = grid["east"], grid["north"]
    srid = int(grid_fiche["columns"][e_col]["srid"])
    half = float(grid["cell_size"]) / 2 if grid.get("coord_ref") == "sw_corner" else 0.0
    pt = f"ST_Point({_ident(e_col)} + {half}, {_ident(n_col)} + {half})"
    rows = con.execute(
        f"SELECT ST_X(p) AS lng, ST_Y(p) AS lat, w FROM ("
        f"  SELECT ST_Transform({pt},"
        f"    'EPSG:{srid}', 'EPSG:4326', always_xy := true) AS p,"
        f"    {_ident(weight_col)}::DOUBLE AS w"
        f"  FROM read_parquet('{data}')) q"
    ).fetchall()
    expo: dict[str, float] = {}
    for lng, lat, w in rows:
        cell = h3.latlng_to_cell(float(lat), float(lng), resolution)
        expo[cell] = expo.get(cell, 0.0) + float(w)
    return expo


def split_cells(
    obs: dict[str, int], expo: dict[str, float]
) -> "tuple[dict[str, int], dict[str, int]]":
    """Sépare cellules testables (exposition>0) et non-peuplées (exposition==0)."""
    testables = {c: o for c, o in obs.items() if expo.get(c, 0.0) > 0.0}
    unpop = {c: o for c, o in obs.items() if expo.get(c, 0.0) <= 0.0}
    return testables, unpop
