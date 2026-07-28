"""Connexion DuckDB read-only bornée — garantit l'invariant P3 (pas d'écriture).

Ouvre le fichier Parquet via une vue DuckDB en deux phases (écriture puis
réouverture read_only) afin que toute tentative DDL/DML lève une erreur.
"""

import tempfile
from pathlib import Path

import duckdb


def open_readonly(parquet_path: str | Path, table: str) -> duckdb.DuckDBPyConnection:
    """Ouvre une connexion DuckDB read-only sur le fichier Parquet donné.

    Procède en deux phases : écriture de la vue dans un fichier .duckdb temporaire,
    puis réouverture en read_only=True. SELECT/read_parquet restent possibles ;
    toute écriture (DDL/DML) est rejetée par DuckDB (vérifié empiriquement).
    """
    if not table.replace("_", "").isalnum():
        raise ValueError(f"nom de table invalide: {table!r}")
    p = Path(parquet_path).as_posix()
    # répertoire temporaire UNIQUE par appel : évite un PermissionError Windows
    # si une connexion read-only précédente tient encore le .duckdb (Windows 11).
    dbfile = Path(tempfile.mkdtemp(prefix="intreepid_")) / f"{table}.duckdb"
    # 1) phase ÉCRITURE : définir la vue dans le fichier, puis fermer.
    w = duckdb.connect(str(dbfile))
    w.execute(f"CREATE VIEW {table} AS SELECT * FROM read_parquet('{p}')")
    w.close()
    # 2) réouverture READ-ONLY : SELECT/read_parquet OK, CREATE/INSERT lèvent Error.
    return duckdb.connect(str(dbfile), read_only=True)
