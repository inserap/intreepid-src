"""Profil de l'agent analyste : options isolées (P2/P3) + parsing du verdict.

Exprime l'analyste (charte, allowlist MCP, isolation des built-ins, verdict
fait/hypothèse/refusé) comme un Profile pour l'orchestrateur générique
(ADR-0009). La mécanique d'exécution vit dans orchestrator.py.
"""

from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions

from intreepid.agent.profile import Profile
from intreepid.agent.verdict import Observation, parse_verdict
from intreepid.scribe.store import Scribe

CHARTER = (Path(__file__).parent / "charter.md").read_text(encoding="utf-8")

_MCP_TOOLS = [
    "mcp__intreepid__list_datasets",
    "mcp__intreepid__describe",
    "mcp__intreepid__profile_stats",
    "mcp__intreepid__concentration_test",
    "mcp__intreepid__spatial_scale_robustness",
]

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


def build_options(
    model: str | None = None, *, thinking: bool = False
) -> ClaudeAgentOptions:
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


def _record_verdict(scribe: Scribe | None, observations: list[Observation]) -> None:
    if scribe is not None:
        scribe.record_nodes(
            [
                (
                    "observation",
                    {"claim": o.claim, "note": o.note},
                    {"statut": o.statut, "confiance": o.confiance, "nature": o.nature},
                )
                for o in observations
            ]
        )


def _parse(chunks: list[str]) -> list[Observation]:
    return parse_verdict("\n".join(chunks))


def analyst_profile() -> Profile:
    return Profile(
        role="analyst",
        build_options=build_options,
        parse=_parse,
        on_result=_record_verdict,
    )
