"""Vérifie le profil curateur : isolation P2/P3, terminaison, validation."""

import yaml

from intreepid.agent.curator.profile import (
    _DISALLOWED,
    _MCP_TOOLS,
    build_options,
    curator_profile,
)
from intreepid.agent.curator.surface import Surface
from intreepid.agent.curator.turn import CuratorTurn


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
        message="prête ?",
        fiche_delta={"dataset": "d", "columns": {"a": {}}},
        proposes_completion=True,
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
    turn = CuratorTurn(message="voici", fiche_delta=None, proposes_completion=False)
    next_input = prof.next_input
    assert next_input is not None
    assert next_input(turn) == "corrige la colonne X"


def test_build_prompt_serializes_transcript(tmp_path):
    prof = curator_profile("d.parquet", tmp_path)
    build_prompt = prof.build_prompt
    assert build_prompt is not None
    out = build_prompt([{"user": "start"}, {"assistant": "salut"}, {"user": "ok"}])
    assert "start" in out and "salut" in out and "ok" in out


def test_next_input_affiche_substitut_si_message_vide(tmp_path):
    vus: list[str] = []
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=vus.append, reader=lambda _p: "reformule"),
    )
    turn = CuratorTurn(message="", fiche_delta=None, proposes_completion=False)
    next_input = prof.next_input
    assert next_input is not None
    result = next_input(turn)
    assert result == "reformule"
    assert any("[tour vide" in t for t in vus)


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
    result = CuratorTurn(message="fini", fiche_delta=draft, proposes_completion=True)
    next_input = prof.next_input
    on_result = prof.on_result
    assert next_input is not None and on_result is not None
    next_input(result)  # alimente l'accumulateur, que `on_result` écrira
    on_result(sc, result)  # type: ignore[arg-type]

    written = tmp_path / "mon_dataset.fiche.yaml"
    assert written.is_file()
    assert sc.specs is not None
    kind, content, meta = sc.specs[0]
    assert kind == "curation_validated"
    assert content["dataset"] == "mon_dataset"
    assert len(meta["hash"]) == 64  # sha256 hex


def test_on_result_ecrit_laccumulateur_et_non_le_dernier_delta(tmp_path):
    """Le test discriminant de la brique #10.

    Trois tours de deltas DISJOINTS : la fiche écrite doit porter les trois
    colonnes. Avec le code d'avant, qui écrivait `result.fiche_delta`, elle n'en
    porterait qu'une.
    """
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=lambda _p: "o"),
    )
    next_input = prof.next_input
    on_result = prof.on_result
    assert next_input is not None and on_result is not None

    next_input(
        CuratorTurn(
            message="t1",
            fiche_delta={"dataset": "mon_dataset", "columns": {"a": {"type": "num"}}},
            proposes_completion=False,
        )
    )
    next_input(
        CuratorTurn(
            message="t2",
            fiche_delta={"columns": {"b": {"type": "cat"}}},
            proposes_completion=False,
        )
    )
    final = CuratorTurn(
        message="prête ?",
        fiche_delta={"columns": {"c": {"type": "temporal"}}},
        proposes_completion=True,
    )
    assert next_input(final) is None  # 'o' => validé
    on_result(None, final)

    ecrite = yaml.safe_load((tmp_path / "mon_dataset.fiche.yaml").read_text("utf-8"))
    assert set(ecrite["columns"]) == {"a", "b", "c"}
    assert ecrite["dataset"] == "mon_dataset"


def test_validation_acceptee_quand_le_dernier_delta_est_vide(tmp_path):
    """Un dernier tour sans nouvelle colonne est désormais le cas NORMAL.

    L'ancienne garde, qui portait sur `fiche_delta is None`, l'aurait refusé.
    """
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=lambda _p: "o"),
    )
    next_input = prof.next_input
    assert next_input is not None
    next_input(
        CuratorTurn(
            message="t1",
            fiche_delta={"columns": {"a": {}}},
            proposes_completion=False,
        )
    )
    final = CuratorTurn(message="prête ?", fiche_delta=None, proposes_completion=True)
    assert next_input(final) is None


def test_validation_refusee_quand_rien_na_jamais_ete_transmis(tmp_path):
    """La garde survit, déplacée sur l'accumulateur.

    Accumulateur vide => valider ne produirait aucune fiche et perdrait la session.
    """
    vus: list[str] = []
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=vus.append, reader=lambda _p: "renvoie la fiche"),
    )
    next_input = prof.next_input
    assert next_input is not None
    turn = CuratorTurn(message="prête ?", fiche_delta=None, proposes_completion=True)
    assert next_input(turn) == "renvoie la fiche"
    assert any("Aucune colonne" in t for t in vus)


def test_build_prompt_porte_linventaire(tmp_path):
    # Surface INJECTÉE : `Surface()` par défaut lit sur `input()`, et ce test
    # appelle `next_input`, qui se termine par `surface.ask()`. Sans injection,
    # pytest lève « reading from stdin while output is captured ».
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=lambda _p: "ok"),
    )
    next_input, build_prompt = prof.next_input, prof.build_prompt
    assert next_input is not None and build_prompt is not None
    next_input(
        CuratorTurn(
            message="t1",
            fiche_delta={"columns": {"alpha": {}, "beta": {}}},
            proposes_completion=False,
        )
    )
    out = build_prompt([{"user": "start"}, {"assistant": "t1"}])
    assert "Brouillon conservé par l'application" in out
    assert "alpha" in out and "beta" in out
    assert "2 colonne" in out


def test_linventaire_ne_contamine_pas_la_reponse_humaine(tmp_path):
    """Contrainte dure : la réponse humaine ne porte QUE des mots de l'humain.

    L'orchestrateur grave la valeur retournée par `next_input` en nœud
    `human_turn` / `actor: "human"`. Y glisser l'inventaire inscrirait dans une
    trace probante des mots que l'humain n'a pas dits — c'est le défaut que la
    passe 2 d'advisor de la brique #8 avait attrapé.
    """
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=lambda _p: "1a"),
    )
    next_input = prof.next_input
    assert next_input is not None
    reponse = next_input(
        CuratorTurn(
            message="t1",
            fiche_delta={"columns": {"alpha": {}}},
            proposes_completion=False,
        )
    )
    assert reponse == "1a"
    assert "Brouillon" not in str(reponse)
