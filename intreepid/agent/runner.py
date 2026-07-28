from pathlib import Path
import os
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock
from intreepid.agent.verdict import parse_verdict, Observation

CHARTER = (Path(__file__).parent / "charter.md").read_text(encoding="utf-8")

_MCP_TOOLS = [
    "mcp__intreepid__list_datasets",
    "mcp__intreepid__describe",
    "mcp__intreepid__profile_stats",
]


def _build_options() -> ClaudeAgentOptions:
    """Construit les options de l'agent avec isolation maximale (invariant P2/P3).

    Config retenue (VÉRIFIÉE EMPIRIQUEMENT par smoke, pas par lecture de source) :
    - disallowed_tools  → retire les built-ins fichier/shell/web + Skill du contexte
                          (barrière PRINCIPALE ; smoke : Bash/Read bloqués, MCP OK)
    - allowed_tools     → auto-approuve UNIQUEMENT les 3 outils MCP intreepid
    - strict_mcp_config → ignore les serveurs MCP ambiants (~/.claude, .mcp.json…)
    - setting_sources=[] → ignore les settings utilisateur/projet (pas de skills tiers)
    - skills=[]         → aucune skill injectée
    NB : `tools=[]` a été essayé puis RETIRÉ — il vide AUSSI les outils MCP (smoke :
    l'agent se retrouve sans aucun outil et ne peut plus profiler). C'est
    `disallowed_tools` qui porte l'isolation des built-ins.
    """
    return ClaudeAgentOptions(
        allowed_tools=_MCP_TOOLS,  # auto-approuve uniquement les 3 outils MCP
        disallowed_tools=[  # barrière principale : retire les built-ins du contexte
            "Bash", "Read", "Write", "Edit", "MultiEdit",
            "Glob", "Grep", "LS",
            "WebSearch", "WebFetch",
            "NotebookRead", "NotebookEdit",
            "Skill",
        ],
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
    )


async def run_analysis(question: str) -> list[Observation]:
    # Garde Q-0010 : dev sur l'abonnement (CLAUDE_CODE_OAUTH_TOKEN). ANTHROPIC_API_KEY
    # masquerait l'OAuth et facturerait l'API → on refuse de tourner si elle est présente.
    if os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY est définie : elle masque CLAUDE_CODE_OAUTH_TOKEN."
            " Unset-la (dev = abonnement)."
        )
    options = _build_options()
    chunks: list[str] = []
    async for message in query(prompt=question, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    chunks.append(block.text)
    return parse_verdict("\n".join(chunks))
