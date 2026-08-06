"""Profil de l'agent curateur : isolation P2/P3, conversation, écriture de fiche.

2ᵉ profil réel de l'orchestrateur générique (ADR-0009, Q-0021). Multi-tours :
`next_input` lit la réponse humaine (None => validé) et ACCUMULE le delta de fiche
du tour (Q-0023 — l'agent n'émet que ses colonnes neuves, cf. `draft.py`) ;
`build_prompt` sérialise l'historique (charte = system_prompt byte-stable) et y
ajoute l'inventaire du brouillon ; `on_result` écrit l'ACCUMULATEUR et grave le
nœud `curation_validated` (hash). La fiche reste un dict quasi opaque : Python n'en
connaît que la clé `columns`, les noms de colonnes, et `dataset` — lu par `_on_result`
pour nommer le fichier écrit, lecture ANTÉRIEURE à cette slice.
"""

import re
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions

from intreepid.agent.curator.draft import inventory_line, merge_delta
from intreepid.agent.curator.fiche_writer import write_fiche
from intreepid.agent.curator.surface import Surface
from intreepid.agent.curator.turn import CuratorTurn, parse_curator_turn
from intreepid.agent.profile import Profile
from intreepid.scribe.store import Scribe

CHARTER = (Path(__file__).parent / "charter.md").read_text(encoding="utf-8")

_MCP_TOOLS = ["mcp__intreepid__profile_raw"]

_DISALLOWED = [
    "Bash",
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "Glob",
    "Grep",
    "LS",
    "WebSearch",
    "WebFetch",
    "NotebookRead",
    "NotebookEdit",
    "Skill",
]

_VALIDATE_WORDS = {"o", "oui", "ok", "valide", "valider", "valid"}


def build_options(
    model: str | None = None, *, thinking: bool = False
) -> ClaudeAgentOptions:
    """Options du curateur avec isolation maximale (P2/P3), calquées sur l'analyste."""
    return ClaudeAgentOptions(
        model=model,
        allowed_tools=_MCP_TOOLS,
        disallowed_tools=_DISALLOWED,
        system_prompt=CHARTER,
        mcp_servers={
            "intreepid": {
                "type": "stdio",
                "command": "uv",
                "args": ["run", "python", "-m", "intreepid.mcp_server.server"],
            }
        },
        permission_mode="bypassPermissions",
        strict_mcp_config=True,
        setting_sources=[],
        skills=[],
        thinking={"type": "adaptive", "display": "summarized"} if thinking else None,
    )


def curator_profile(
    dataset_path: str,
    catalog_dir: str | Path,
    surface: Surface | None = None,
) -> Profile:
    surface = surface or Surface()
    catalog_dir = Path(catalog_dir)

    # Brouillon tenu par l'APPLICATION (Q-0023) : l'agent n'émet que ses deltas,
    # et c'est ce dict-ci qui porte la fiche complète d'un tour à l'autre.
    brouillon: dict[str, Any] = {}

    def _next_input(result: CuratorTurn) -> str | None:
        nonlocal brouillon
        brouillon = merge_delta(brouillon, result.fiche_delta)
        surface.show(result.message or "[tour vide — demande-lui de reformuler]")
        if result.proposes_completion:
            if not brouillon.get("columns"):
                # La garde porte sur l'ACCUMULATEUR, plus sur le delta du tour :
                # un dernier tour sans nouvelle colonne est désormais le cas
                # normal. Valider avec un accumulateur vide perdrait la session.
                # On ne relance PAS tout seul : une relance automatique boucle
                # sans borne et s'inscrirait dans la trace comme un tour humain.
                surface.show(
                    "\n[Aucune colonne transmise — rien ne serait écrit en l'état."
                    " Demande-lui de transmettre la fiche, ou Ctrl+C.]"
                )
                return surface.ask()
            surface.show("\n[Valider ? 'o' = valider, sinon tape une correction]")
            reply = surface.ask()
            if reply.strip().lower() in _VALIDATE_WORDS:
                return None  # validé => terminal
            return reply
        return surface.ask()

    def _on_result(scribe: Scribe | None, result: CuratorTurn) -> None:
        # MÊME condition que la garde de `_next_input` : deux formulations
        # différentes ("brouillon vide" vs "pas de colonnes") laisseraient un
        # accumulateur du genre {"dataset": "d"} refusé à la validation mais
        # écrit ici. Inatteignable aujourd'hui, ambigu à la lecture.
        if not brouillon.get("columns"):
            surface.show("Aucune fiche à écrire (aucune colonne transmise).")
            return
        raw = str(brouillon.get("dataset") or Path(dataset_path).stem)
        # garde : nom de fichier sûr (pas de slash/point)
        # => pas d'écriture hors catalog_dir
        dataset = re.sub(r"[^0-9A-Za-z_]", "_", Path(raw).stem)
        path = catalog_dir / f"{dataset}.fiche.yaml"
        try:
            h = write_fiche(brouillon, path)
        except Exception as e:  # feedback humain garanti (on_result est best-effort)
            surface.show(f"✗ échec écriture fiche : {e!r}")
            raise
        surface.show(f"✓ fiche écrite : {path} (sha256 {h[:12]}…)")
        if scribe is not None:
            scribe.record_nodes(
                [
                    (
                        "curation_validated",
                        {"path": str(path), "dataset": dataset},
                        {"hash": h, "actor": "human"},
                    )
                ]
            )

    def _serialize(transcript: list[dict[str, str]]) -> str:
        lines = ["Historique de la curation :"]
        for turn in transcript:
            for role, text in turn.items():
                who = "HUMAIN" if role == "user" else "TOI"
                lines.append(f"[{who}] {text}")
        # Canal APPLICATION-OWNED (ADR-0009) : l'inventaire passe par le prompt,
        # jamais par la réponse humaine, qui est gravée en `human_turn`.
        lines.append(f"\n{inventory_line(brouillon)}")
        lines.append("\nContinue la curation en respectant ton format de sortie.")
        return "\n".join(lines)

    return Profile(
        role="curator",
        build_options=build_options,
        parse=lambda chunks: parse_curator_turn("\n".join(chunks)),
        on_result=_on_result,
        next_input=_next_input,
        build_prompt=_serialize,
    )
