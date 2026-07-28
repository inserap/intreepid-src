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

    Config retenue (vérifiée sur le source SDK 0.2.128) :
    - tools=[]          → --tools ""  : base built-ins vide (fichier, shell, web…)
    - allowed_tools     → --allowedTools : seuls les 3 outils MCP intreepid autorisés
    - disallowed_tools  → défense-en-profondeur redondante (garde si tools= change)
    - strict_mcp_config → --strict-mcp-config : bloque les serveurs MCP ambiants
    - setting_sources=[] → --setting-sources= : bloque les settings utilisateur/projet
    - skills=[]         → pas d'injection Skill dans allowed_tools
    MCP tools sont toujours actifs : tools= et allowed_tools opèrent sur des listes
    orthogonales (built-ins vs. MCP), confirmé par subprocess_cli.py lignes 479–495.
    """
    return ClaudeAgentOptions(
        tools=[],  # désactive tous les built-ins (Bash, Read, Write, Web…)
        allowed_tools=_MCP_TOOLS,  # allowlist explicite MCP-only
        disallowed_tools=[  # défense-en-profondeur
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
