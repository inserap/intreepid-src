"""Démo du curateur : curation conversationnelle réelle d'un dataset non-fiché.

Usage : uv run python -m intreepid.demo_curator <chemin.parquet>
Modèle opus ; garde OAuth Q-0010 (CLAUDE_CODE_OAUTH_TOKEN, pas ANTHROPIC_API_KEY).
Gate humain : l'humain dialogue au terminal, relit le YAML final, valide.
La trace est conservée dans traces/ (*.duckdb gitignorés) ; relecture :
  uv run python -m intreepid.metrics_report traces/<fichier>.duckdb
Le thinking est demandé explicitement (les nœuds 💭 de la trace en dépendent).
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


def _preuve_et_mesures(db: Path) -> str:
    """Bloc de fin de séance : preuve greffier + mesures, en TEXTE.

    Retourne au lieu d'imprimer, pour être vérifiable sans lancer un agent.
    Ne se tait jamais : une base sans session produit un constat explicite,
    parce que le gate a besoin de savoir que la preuve manque.
    """
    con = duckdb.connect(str(db), read_only=True)
    try:
        row = con.execute("SELECT session_id FROM sessions").fetchone()
    finally:
        con.close()
    if row is None:
        return (
            "\n(trace présente mais AUCUNE session enregistrée :"
            " ni preuve greffier ni mesures — à signaler au gate)"
        )
    tr = load(db, str(row[0]))
    validated = [n for n in tr.nodes if n.kind == "curation_validated"]
    human_turns = sum(1 for n in tr.nodes if n.kind == "human_turn")
    lignes = [
        "\n--- preuve greffier ---",
        f"statut session           : {tr.status}",
        f"tours humains            : {human_turns}",
        f"nœuds curation_validated : {len(validated)}",
    ]
    if validated:
        lignes.append(f"  dataset : {validated[0].content.get('dataset')}")
        lignes.append(f"  hash    : {str(validated[0].meta.get('hash', ''))[:16]}…")
    lignes.append("\n--- mesures ---")
    lignes.append(render_metrics(summarize(tr)))
    return "\n".join(lignes)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: uv run python -m intreepid.demo_curator <chemin.parquet>"
        )
    dataset_path = sys.argv[1]
    prompt = (
        f"Curate le dataset non-fiché situé à : {dataset_path}\n"
        f"Commence par appeler profile_raw sur ce chemin, puis dialogue avec moi "
        f"jusqu'à une fiche complète."
    )
    profile = curator_profile(dataset_path, CATALOG, surface=Surface())
    traces = Path(__file__).parent.parent / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    db = traces / f"curator-{uuid.uuid4().hex[:8]}.duckdb"
    try:
        anyio.run(
            lambda: run_agent(profile, prompt, model="opus", trace_to=db, thinking=True)
        )
    finally:
        # Quoi qu'il arrive (interruption clavier, exception), on dit la vérité sur
        # ce qui existe : c'est la session dont on veut le coût. Le bloc de preuve
        # est DANS le finally : un Ctrl+C en cours de séance est précisément le cas
        # où l'on veut la preuve et les mesures, pas celui où on les perd.
        if db.is_file():
            print(f"\ntrace conservée : {db}")
            print(f"  relecture : uv run python -m intreepid.metrics_report {db}")
            try:
                print(_preuve_et_mesures(db))
            except Exception as e:
                # Dans un `finally`, une exception d'affichage REMPLACERAIT
                # l'exception d'origine (le Ctrl+C qu'on veut voir remonter).
                # On ne se tait pas, et on n'avale pas l'interruption.
                print(f"\n(preuve indisponible : {e!r})")
        else:
            # l'orchestrateur poursuit sans greffier si l'ouverture échoue : la base
            # peut manquer alors que la conversation, elle, a bien eu lieu.
            print("\n(aucune trace écrite : capture désactivée pendant ce run)")


if __name__ == "__main__":
    main()
