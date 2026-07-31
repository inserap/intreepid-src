"""Démo du greffier : enregistre une session de l'analyste puis rejoue l'arbre capturé.

Usage : uv run python -m intreepid.demo_greffier
"""

import tempfile
from pathlib import Path

import anyio
import duckdb

from intreepid.agent.runner import run_analysis
from intreepid.scribe.render import render
from intreepid.scribe.store import load

QUESTION = (
    "Profile les colonnes du dataset et rends ton verdict : y a-t-il des valeurs "
    "suspectes ? peut-on conclure une tendance du monde réel depuis un volume ?"
)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="greffier_demo_") as tmp:
        db = Path(tmp) / "episodic.duckdb"
        print("=== run analyste (enregistré) ===")
        verdict = anyio.run(lambda: run_analysis(QUESTION, trace_to=db))
        for o in verdict:
            print(f"- [{o.statut}] {o.claim}")
        con = duckdb.connect(str(db), read_only=True)
        try:
            row = con.execute("SELECT session_id FROM sessions").fetchone()
        finally:
            con.close()
        sid: str | None = str(row[0]) if row else None
        if sid is None:
            raise RuntimeError("No session found in database")
        print("\n=== arbre de session rejoué (load → render) ===")
        print(render(load(db, sid)))


if __name__ == "__main__":
    main()
