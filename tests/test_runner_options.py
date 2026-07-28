"""Test-garde déterministe pour l'invariant P2/P3 (isolation des outils).

N'est PAS marqué @pytest.mark.agent : ne lance pas l'agent, ne touche pas le réseau.
Appelle _build_options() et asserte le verrouillage statique.
Échouera si une modification future rouvre la surface d'attaque.
"""

from intreepid.agent.runner import _MCP_TOOLS, _build_options


def test_mcp_tools_are_sole_allowed():
    """allowed_tools = exactement les 3 outils MCP intreepid, rien d'autre."""
    opts = _build_options()
    assert sorted(opts.allowed_tools) == sorted(_MCP_TOOLS), (
        f"allowed_tools doit être exactement {_MCP_TOOLS}, got {opts.allowed_tools}"
    )


def test_builtins_isolated_via_disallowed():
    """Isolation des built-ins via disallowed_tools.

    `tools=[]` a été retiré car il vide AUSSI les outils MCP (vérifié par smoke :
    l'agent se retrouve sans aucun outil). L'isolation P2/P3 repose donc sur
    disallowed_tools, qui doit contenir l'ensemble complet des built-ins
    fichier/shell/web + Skill.
    """
    opts = _build_options()
    required = {
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
    }
    missing = required - set(opts.disallowed_tools)
    assert not missing, f"built-ins non isolés dans disallowed_tools : {missing}"


def test_dangerous_builtins_in_disallowed():
    """Défense-en-profondeur : les built-ins dangereux sont dans disallowed_tools."""
    opts = _build_options()
    dangerous = {"Bash", "Read", "Write", "Edit", "WebSearch", "WebFetch", "Skill"}
    missing = dangerous - set(opts.disallowed_tools)
    assert not missing, (
        f"Ces outils dangereux manquent dans disallowed_tools : {missing}"
    )


def test_strict_mcp_config():
    """strict_mcp_config=True → bloque les serveurs MCP ambiants.

    Couvre ~/.claude et .mcp.json (serveurs injectés par l'environnement).
    """
    opts = _build_options()
    assert opts.strict_mcp_config is True


def test_setting_sources_empty():
    """setting_sources=[] → aucun fichier de settings utilisateur/projet chargé."""
    opts = _build_options()
    assert opts.setting_sources == [], (
        f"setting_sources doit être [] pour bloquer les settings ambiants, "
        f"got {opts.setting_sources!r}"
    )


def test_skills_empty():
    """skills=[] → pas d'injection automatique de l'outil Skill dans allowed_tools."""
    opts = _build_options()
    assert opts.skills == [], (
        f"skills doit être [] pour bloquer les skills ambiants, got {opts.skills!r}"
    )


def test_no_debug_stderr_dead_code():
    """debug_stderr n'est plus surchargé dans _build_options (dead code retiré).

    L'ancien code injectait un io.TextIOWrapper ouvert sur fd=2 avec closefd=False.
    On vérifie que _build_options() ne passe pas non plus de stderr= (callback) :
    le SDK ne pipe stderr que si stderr != None (subprocess_cli.py l. 731).
    """
    opts = _build_options()
    assert opts.stderr is None, (
        "stderr callback ne doit pas être injecté par _build_options"
    )
