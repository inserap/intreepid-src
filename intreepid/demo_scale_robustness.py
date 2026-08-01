"""Démo brique #6 : robustesse d'échelle spatiale sur les accidents réels.

Lance l'analyste (données OFROU réelles + exposition STATPOP), capture la
session, génère le notebook Quarto. Gate humain AVANT merge.
  uv run python -m intreepid.demo_scale_robustness
"""

import os
import sys
from pathlib import Path

import anyio
import duckdb

# Windows : la console legacy (cp1252) plante à l'impression des caractères du
# verdict hors cp1252 (≈, ±) → UnicodeEncodeError. Forcer UTF-8, filet errors=replace.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

CATALOG = Path(__file__).parent.parent / "catalog"
os.environ["INTREEPID_FICHE"] = str(CATALOG / "accidents_route.fiche.yaml")

from intreepid.agent.runner import run_analysis  # noqa: E402
from intreepid.scribe.notebook import render_html, to_quarto  # noqa: E402
from intreepid.scribe.store import load  # noqa: E402

QUESTION = (
    "Teste la robustesse d'échelle de la concentration spatiale : la "
    "sur-concentration des points (au-delà de l'exposition déclarée dans la "
    "fiche) survit-elle au changement de maille H3 ? Utilise l'outil "
    "spatial_scale_robustness, puis interprète le verdict, les per_resolution "
    "(pic, part unpopulated) et les caveats avec la réserve d'exposition "
    "documentée dans la fiche."
)


def main() -> None:
    out_dir = Path(__file__).parent.parent / "data" / "prepared"
    out_dir.mkdir(parents=True, exist_ok=True)
    db = out_dir / "session_brique6.duckdb"
    if db.exists():
        db.unlink()  # store append-only : repartir propre pour la démo
    print("=== run analyste (RÉEL, enregistré) ===")
    verdict = anyio.run(lambda: run_analysis(QUESTION, trace_to=db))
    for o in verdict:
        print(f"- [{o.statut}] {o.claim}")
    con = duckdb.connect(str(db), read_only=True)
    try:
        row = con.execute("SELECT session_id FROM sessions").fetchone()
    finally:
        con.close()
    if row is None:
        raise RuntimeError("aucune session capturée")
    trace = load(db, str(row[0]))
    qmd = out_dir / "session_brique6.qmd"
    qmd.write_text(to_quarto(trace), encoding="utf-8")
    print(f"\n=== notebook généré : {qmd} ===")
    html = render_html(qmd)
    print(f"HTML : {html}" if html else "HTML : (quarto absent, .qmd seul)")


if __name__ == "__main__":
    main()
