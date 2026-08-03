"""Vérifie le profil curateur : isolation P2/P3, terminaison, validation."""

from intreepid.agent.curator.surface import Surface
from intreepid.agent.curator.turn import CuratorTurn
from intreepid.agent.curator_profile import (
    _DISALLOWED,
    _MCP_TOOLS,
    build_options,
    curator_profile,
)


def test_allowlist_is_profile_raw_only():
    assert _MCP_TOOLS == ["mcp__intreepid__profile_raw"]


def test_isolation_disallows_builtins():
    opts = build_options()
    for tool in ("Bash", "Read", "Write", "WebFetch", "Skill"):
        assert tool in _DISALLOWED
    assert opts.allowed_tools == _MCP_TOOLS
    assert opts.disallowed_tools == _DISALLOWED
    assert opts.permission_mode == "bypassPermissions"
    assert opts.setting_sources == []
    assert opts.strict_mcp_config is True


def test_next_input_returns_none_on_validation(tmp_path):
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=lambda _p: "o"),
    )
    turn = CuratorTurn(
        message="prête ?", fiche_draft={"dataset": "d"}, proposes_completion=True
    )
    next_input = prof.next_input
    assert next_input is not None
    assert next_input(turn) is None  # 'o' => validé


def test_next_input_returns_reply_when_not_complete(tmp_path):
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(
            writer=lambda _t: None, reader=lambda _p: "corrige la colonne X"
        ),
    )
    turn = CuratorTurn(message="voici", fiche_draft=None, proposes_completion=False)
    next_input = prof.next_input
    assert next_input is not None
    assert next_input(turn) == "corrige la colonne X"


def test_build_prompt_serializes_transcript(tmp_path):
    prof = curator_profile("d.parquet", tmp_path)
    build_prompt = prof.build_prompt
    assert build_prompt is not None
    out = build_prompt([{"user": "start"}, {"assistant": "salut"}, {"user": "ok"}])
    assert "start" in out and "salut" in out and "ok" in out


def test_on_result_writes_fiche_and_records_validation(tmp_path):
    class _Scribe:
        def __init__(self):
            self.specs = None

        def record_nodes(self, specs):
            self.specs = specs

    sc = _Scribe()
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=lambda _p: ""),
    )
    draft = {"dataset": "mon_dataset", "columns": {"a": {"type": "numeric"}}}
    result = CuratorTurn(message="fini", fiche_draft=draft, proposes_completion=True)
    on_result = prof.on_result
    assert on_result is not None
    on_result(sc, result)  # type: ignore[arg-type]

    written = tmp_path / "mon_dataset.fiche.yaml"
    assert written.is_file()
    assert sc.specs is not None
    kind, content, meta = sc.specs[0]
    assert kind == "curation_validated"
    assert content["dataset"] == "mon_dataset"
    assert len(meta["hash"]) == 64  # sha256 hex
