"""Démo montrable en CLI : profile_stats brut suivi du verdict de l'agent.

Usage : python -m intreepid.demo
"""

import json
from pathlib import Path

import anyio

from intreepid.agent.runner import run_analysis
from intreepid.mcp_server.bounds import open_readonly
from intreepid.mcp_server.catalog import load_fiche
from intreepid.mcp_server.profile_stats import profile_stats

FIX = Path(__file__).parent.parent / "fixtures"
QUESTION = (
    "Profile accidents_route : accidents plus graves en fin d'année ? "
    "valeurs suspectes ? Rends ton verdict."
)


def main():
    fiche = load_fiche(FIX / "accidents.fiche.yaml")
    with open_readonly(FIX / "accidents_seed.parquet", "accidents_route") as con:
        print("=== profile_stats (brut) ===")
        print(
            json.dumps(
                profile_stats(con, "accidents_route", fiche),
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
    print("\n=== verdict de l'agent ===")
    for o in anyio.run(run_analysis, QUESTION):
        print(f"- [{o.statut}] {o.claim}" + (f"  ({o.note})" if o.note else ""))


if __name__ == "__main__":
    main()
