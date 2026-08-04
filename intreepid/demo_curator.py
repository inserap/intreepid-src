"""Démo du curateur : curation conversationnelle réelle d'un dataset non-fiché.

Usage : uv run python -m intreepid.demo_curator <chemin.parquet>
Modèle opus ; garde OAuth Q-0010 (CLAUDE_CODE_OAUTH_TOKEN, pas ANTHROPIC_API_KEY).
Gate humain : l'humain dialogue au terminal, relit le YAML final, valide.
La trace est conservée dans traces/ (*.duckdb gitignorés) ; relecture :
  uv run python -m intreepid.metrics_report traces/<fichier>.duckdb
"""

import sys
import uuid
from pathlib import Path

import anyio
import duckdb

from intreepid.agent.curator.profile import curator_profile
from intreepid.agent.curator.surface import Surface
from intreepid.agent.orchestrator import run_agent
from intreepid.scribe.metrics import render_metrics, summarize
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
    traces = Path(__file__).parent.parent / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    db = traces / f"curator-{uuid.uuid4().hex[:8]}.duckdb"
    anyio.run(lambda: run_agent(profile, prompt, model="opus", trace_to=db))
    if not db.is_file():
        # l'orchestrateur poursuit sans greffier si l'ouverture échoue : la base
        # peut donc manquer alors que la conversation, elle, a bien eu lieu.
        print("\n(aucune trace écrite : capture désactivée pendant ce run)")
        return
    con = duckdb.connect(str(db), read_only=True)
    try:
        row = con.execute("SELECT session_id FROM sessions").fetchone()
    finally:
        con.close()
    if row is not None:
        tr = load(db, str(row[0]))
        validated = [n for n in tr.nodes if n.kind == "curation_validated"]
        human_turns = sum(1 for n in tr.nodes if n.kind == "human_turn")
        print("\n--- preuve greffier ---")
        print(f"statut session           : {tr.status}")
        print(f"tours humains            : {human_turns}")
        print(f"nœuds curation_validated : {len(validated)}")
        if validated:
            print(f"  dataset : {validated[0].content.get('dataset')}")
            print(f"  hash    : {str(validated[0].meta.get('hash', ''))[:16]}…")
        print("\n--- mesures ---")
        print(render_metrics(summarize(tr)))
    print(f"\ntrace conservée : {db}")
    print(f"  relecture : uv run python -m intreepid.metrics_report {db}")


if __name__ == "__main__":
    main()
