"""Pilote l'agent analyste — wrapper mince sur l'orchestrateur générique (ADR-0009).

Conserve la signature publique `run_analysis` (non-régression) ; délègue la
mécanique à `orchestrator.run_agent`, l'analyste étant décrit par `analyst_profile`.
`_build_options`/`_MCP_TOOLS` restent exposés (garde-tests d'isolation P2/P3).
"""

from pathlib import Path

from intreepid.agent.analyst_profile import _MCP_TOOLS as _MCP_TOOLS
from intreepid.agent.analyst_profile import analyst_profile
from intreepid.agent.analyst_profile import build_options as _build_options
from intreepid.agent.orchestrator import run_agent
from intreepid.agent.verdict import Observation

__all__ = ["run_analysis", "_build_options", "_MCP_TOOLS"]


async def run_analysis(
    question: str,
    model: str | None = "opus",
    trace_to: str | Path | None = None,
) -> list[Observation]:
    # Non-régression stricte : l'analyste conserve le comportement historique
    # (thinking capturé quand — et seulement quand — la session est tracée).
    # Le choix du thinking sur ses propres mérites est un follow-up.
    return await run_agent(
        analyst_profile(),
        question,
        model=model,
        trace_to=trace_to,
        thinking=trace_to is not None,
    )
