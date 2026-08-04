"""Relit une trace existante et imprime ses mesures de temps et de coût.

Usage : uv run python -m intreepid.metrics_report <trace.duckdb> [session_id]
Lecture seule (P4). Sans session_id, prend l'unique session ; s'il y en a
plusieurs, les liste et s'arrête plutôt que d'en choisir une au hasard.
"""

import sys
from pathlib import Path

import duckdb

from intreepid.scribe.metrics import render_metrics, summarize
from intreepid.scribe.store import load


def _sessions(db: Path) -> list[str]:
    con = duckdb.connect(str(db), read_only=True)
    try:
        return [
            str(r[0]) for r in con.execute("SELECT session_id FROM sessions").fetchall()
        ]
    finally:
        con.close()


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: uv run python -m intreepid.metrics_report "
            "<trace.duckdb> [session_id]"
        )
    db = Path(sys.argv[1])
    if not db.is_file():
        raise SystemExit(f"trace introuvable : {db}")
    if len(sys.argv) > 2:
        sid = sys.argv[2]
    else:
        trouvees = _sessions(db)
        if not trouvees:
            raise SystemExit(f"aucune session dans {db}")
        if len(trouvees) > 1:
            raise SystemExit(
                f"{len(trouvees)} sessions dans {db} — préciser un session_id parmi :\n"
                + "\n".join(f"  {s}" for s in trouvees)
            )
        sid = trouvees[0]
    try:
        trace = load(db, sid)
    except KeyError:  # message humain plutôt qu'une trace Python brute
        raise SystemExit(f"session introuvable dans {db} : {sid}") from None
    print(render_metrics(summarize(trace)))


if __name__ == "__main__":
    main()
