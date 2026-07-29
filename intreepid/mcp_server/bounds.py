"""Connexion DuckDB read-only bornée — garantit l'invariant P3 (pas d'écriture).

Ouvre le fichier Parquet via une vue DuckDB en deux phases (écriture puis
réouverture read_only) afin que toute tentative DDL/DML lève une erreur.
Fourni comme context manager : la connexion et son dossier temporaire sont
libérés déterministement en sortie (fermeture AVANT nettoyage du dossier —
garde anti-PermissionError Windows), même dans un serveur long-lived.
"""

import contextlib
import tempfile
from collections.abc import Iterator
from pathlib import Path

import duckdb


@contextlib.contextmanager
def open_readonly(
    parquet_path: str | Path, table: str
) -> Iterator[duckdb.DuckDBPyConnection]:
    """Ouvre une connexion DuckDB read-only sur le fichier Parquet donné.

    Deux phases : écriture de la vue dans un .duckdb temporaire, puis réouverture
    read_only=True. L'extension spatial est chargée (SELECT/read_parquet OK ;
    toute écriture DDL/DML rejetée). En sortie : fermeture puis nettoyage du dossier.
    """
    if not table.replace("_", "").isalnum():
        raise ValueError(f"nom de table invalide: {table!r}")
    p = Path(parquet_path).as_posix()
    with tempfile.TemporaryDirectory(prefix="intreepid_") as tmp:
        dbfile = Path(tmp) / f"{table}.duckdb"
        # 1) phase ÉCRITURE : définir la vue dans le fichier, puis fermer.
        w = duckdb.connect(str(dbfile))
        w.execute(f"CREATE VIEW {table} AS SELECT * FROM read_parquet('{p}')")
        w.close()
        # 2) réouverture READ-ONLY : SELECT/read_parquet OK, CREATE/INSERT lèvent Error.
        con = duckdb.connect(str(dbfile), read_only=True)
        con.execute("INSTALL spatial")
        con.execute("LOAD spatial")
        try:
            yield con
        finally:
            con.close()  # fermer AVANT que TemporaryDirectory ne nettoie (Windows).
