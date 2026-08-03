"""Profil de l'agent curateur : isolation P2/P3, conversation, écriture de fiche.

2ᵉ profil réel de l'orchestrateur générique (ADR-0009, Q-0021). Multi-tours :
`next_input` lit la réponse humaine (None => validé) ; `build_prompt` sérialise
l'historique (la charte = system_prompt byte-stable) ; `on_result` écrit la fiche
validée et grave le nœud `curation_validated` (hash). La fiche reste un dict opaque.
"""

import re
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions

from intreepid.agent.curator.fiche_writer import write_fiche
from intreepid.agent.curator.surface import Surface
from intreepid.agent.curator.turn import CuratorTurn, parse_curator_turn
from intreepid.agent.profile import Profile
from intreepid.scribe.store import Scribe

CHARTER = (Path(__file__).parent / "curator_charter.md").read_text(encoding="utf-8")

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


def _serialize(transcript: list[dict[str, str]]) -> str:
    lines = ["Historique de la curation :"]
    for turn in transcript:
        for role, text in turn.items():
            who = "HUMAIN" if role == "user" else "TOI"
            lines.append(f"[{who}] {text}")
    lines.append("\nContinue la curation en respectant ton format de sortie.")
    return "\n".join(lines)


def curator_profile(
    dataset_path: str,
    catalog_dir: str | Path,
    surface: Surface | None = None,
) -> Profile:
    surface = surface or Surface()
    catalog_dir = Path(catalog_dir)

    def _next_input(result: CuratorTurn) -> str | None:
        surface.show(result.message)
        if result.proposes_completion:
            surface.show("\n[Valider ? 'o' = valider, sinon tape une correction]")
            reply = surface.ask()
            if reply.strip().lower() in _VALIDATE_WORDS:
                return None  # validé => terminal
            return reply
        return surface.ask()

    def _on_result(scribe: Scribe | None, result: CuratorTurn) -> None:
        if result.fiche_draft is None:
            surface.show("Aucune fiche à écrire (draft vide).")
            return
        raw = str(result.fiche_draft.get("dataset") or Path(dataset_path).stem)
        # garde : nom de fichier sûr (pas de slash/point)
        # => pas d'écriture hors catalog_dir
        dataset = re.sub(r"[^0-9A-Za-z_]", "_", Path(raw).stem)
        path = catalog_dir / f"{dataset}.fiche.yaml"
        try:
            h = write_fiche(result.fiche_draft, path)
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

    return Profile(
        role="curator",
        build_options=build_options,
        parse=lambda chunks: parse_curator_turn("\n".join(chunks)),
        on_result=_on_result,
        next_input=_next_input,
        build_prompt=_serialize,
    )
