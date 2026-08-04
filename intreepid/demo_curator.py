"""Démo du curateur : curation conversationnelle réelle d'un dataset non-fiché.

Usage : uv run python -m intreepid.demo_curator <chemin.parquet>
Modèle opus ; garde OAuth Q-0010 (CLAUDE_CODE_OAUTH_TOKEN, pas ANTHROPIC_API_KEY).
Gate humain : l'humain dialogue au terminal, relit le YAML final, valide.
"""

import sys
import tempfile
from pathlib import Path

import anyio
import duckdb

from intreepid.agent.curator.profile import curator_profile
from intreepid.agent.curator.surface import Surface
from intreepid.agent.orchestrator import run_agent
from intreepid.scribe.store import load

CATALOG = Path(__file__).parent.parent / "catalog"


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: uv run python -m intreepid.demo_curator <chemin.parquet>"
        )
    dataset_path = sys.argv[1]
    prompt = (
        f"Curate le dataset non-fiché situé à : {dataset_path}\n"
        f"Commence par appeler profile_raw sur ce chemin, puis dialogue avec moi "
        f"colonne par colonne jusqu'à une fiche complète."
    )
    profile = curator_profile(dataset_path, CATALOG, surface=Surface())
    with tempfile.TemporaryDirectory(prefix="curator_demo_") as tmp:
        db = Path(tmp) / "curation.duckdb"
        anyio.run(lambda: run_agent(profile, prompt, model="opus", trace_to=db))
        # Preuve greffier résumée AVANT fermeture du tmp (la trace est éphémère) :
        # le livrable durable est la fiche écrite dans catalog/ ; la trace, elle,
        # ne sert qu'à attester la validation (nœud curation_validated).
        con = duckdb.connect(str(db), read_only=True)
        try:
            row = con.execute("SELECT session_id FROM sessions").fetchone()
        finally:
            con.close()
        if row is not None:
            tr = load(db, str(row[0]))
            validated = [n for n in tr.nodes if n.kind == "curation_validated"]
            human_turns = sum(1 for n in tr.nodes if n.kind == "human_turn")
            print("\n--- preuve greffier (trace éphémère, résumée ici) ---")
            print(f"statut session           : {tr.status}")
            print(f"tours humains            : {human_turns}")
            print(f"nœuds curation_validated : {len(validated)}")
            if validated:
                print(f"  dataset : {validated[0].content.get('dataset')}")
                print(f"  hash    : {str(validated[0].meta.get('hash', ''))[:16]}…")


if __name__ == "__main__":
    main()
