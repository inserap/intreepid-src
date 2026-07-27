from pathlib import Path
import tempfile
import duckdb

def open_readonly(parquet_path: str | Path, table: str):
    """Ouvre une base FICHIER .duckdb où la vue est définie, puis la rouvre en
    read_only=True. SELECT/read_parquet via la vue restent possibles ; toute
    écriture (DDL/DML) est rejetée par DuckDB (vérifié empiriquement, MUST advisor)."""
    p = Path(parquet_path).as_posix()
    # répertoire temporaire UNIQUE par appel : évite un PermissionError Windows si une
    # connexion read-only précédente tient encore le .duckdb (SHOULD advisor, env Windows 11).
    dbfile = Path(tempfile.mkdtemp(prefix="intreepid_")) / f"{table}.duckdb"
    # 1) phase ÉCRITURE : définir la vue dans le fichier, puis fermer.
    w = duckdb.connect(str(dbfile))
    w.execute(f"CREATE VIEW {table} AS SELECT * FROM read_parquet('{p}')")
    w.close()
    # 2) réouverture READ-ONLY : SELECT/read_parquet OK, CREATE/INSERT lèvent duckdb.Error.
    return duckdb.connect(str(dbfile), read_only=True)
