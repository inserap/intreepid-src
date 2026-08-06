"""Vérifie l'orchestrateur one-shot : parsing + garde OAuth (test déterministe)."""

import pytest
from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock

from intreepid.agent.orchestrator import run_agent
from intreepid.agent.profile import Profile


def _text_profile(on_result=None) -> Profile:
    return Profile(
        role="test",
        build_options=lambda model, thinking: ClaudeAgentOptions(),
        parse=lambda chunks: "\n".join(chunks).strip().upper(),
        on_result=on_result,
    )


async def test_run_agent_oneshot_returns_parsed(monkeypatch):
    async def fake_query(*, prompt, options):
        yield AssistantMessage(content=[TextBlock(text="result")], model="m")

    monkeypatch.setattr("intreepid.agent.orchestrator.query", fake_query)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    out = await run_agent(_text_profile(), "hi")
    assert out == "RESULT"


async def test_run_agent_calls_on_result_and_captures(monkeypatch, tmp_path):
    async def fake_query(*, prompt, options):
        yield AssistantMessage(content=[TextBlock(text="v")], model="m")

    monkeypatch.setattr("intreepid.agent.orchestrator.query", fake_query)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    seen: list = []
    prof = _text_profile(on_result=lambda scribe, result: seen.append(result))
    out = await run_agent(prof, "hi", trace_to=tmp_path / "ep.duckdb")
    assert out == "V"
    assert seen == ["V"]  # on_result reçoit le résultat parsé
    assert (tmp_path / "ep.duckdb").exists()  # capture greffier via run_agent


async def test_run_agent_refuses_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-x")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        await run_agent(_text_profile(), "hi")


def _script_profile(replies, sink):
    """Profil multi-tours factice : parse le texte en dict {'msg','done'}.

    next_input consomme `replies` (None => validé) ; build_prompt sérialise.
    """
    from intreepid.agent.profile import Profile

    it = iter(replies)

    def _parse(chunks):
        text = "\n".join(chunks)
        return {"msg": text, "done": text.strip() == "FINI"}

    def _next_input(result):
        if result["done"]:
            return None  # validé => terminal
        return next(it)

    def _build_prompt(transcript):
        return " | ".join(
            f"{role}:{txt}" for turn in transcript for role, txt in turn.items()
        )

    def _on_result(scribe, result):
        sink.append(("validated", result))

    return Profile(
        role="curator-fake",
        build_options=lambda model, thinking: __import__(
            "claude_agent_sdk"
        ).ClaudeAgentOptions(),
        parse=_parse,
        on_result=_on_result,
        next_input=_next_input,
        build_prompt=_build_prompt,
    )


async def test_run_agent_multiturn_loops_until_validation(monkeypatch, tmp_path):
    turns = iter(["continue", "FINI"])

    async def fake_query(*, prompt, options):
        from claude_agent_sdk import AssistantMessage, TextBlock

        yield AssistantMessage(content=[TextBlock(text=next(turns))], model="m")

    monkeypatch.setattr("intreepid.agent.orchestrator.query", fake_query)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sink: list = []
    prof = _script_profile(replies=["ok, continue stp"], sink=sink)
    result = await run_agent(prof, "start", trace_to=tmp_path / "cur.duckdb")

    assert result["done"] is True
    assert sink == [("validated", result)]  # on_result appelé une fois, à la validation


async def test_run_agent_multiturn_records_human_turns(monkeypatch, tmp_path):
    from intreepid.scribe.store import load

    turns = iter(["continue", "FINI"])

    async def fake_query(*, prompt, options):
        from claude_agent_sdk import AssistantMessage, TextBlock

        yield AssistantMessage(content=[TextBlock(text=next(turns))], model="m")

    monkeypatch.setattr("intreepid.agent.orchestrator.query", fake_query)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    db = tmp_path / "cur.duckdb"
    prof = _script_profile(replies=["ma réponse humaine"], sink=[])
    await run_agent(prof, "start", trace_to=db)

    tr = load(db, _only_session(db))
    kinds = [n.kind for n in tr.nodes]
    assert "human_turn" in kinds
    human = next(n for n in tr.nodes if n.kind == "human_turn")
    assert human.content["text"] == "ma réponse humaine"
    assert human.meta["actor"] == "human"
    assert tr.status == "closed"  # scellé une seule fois en sortie


def _only_session(db):
    import duckdb

    con = duckdb.connect(str(db), read_only=True)
    try:
        row = con.execute("SELECT session_id FROM sessions").fetchone()
        assert row is not None
        return str(row[0])
    finally:
        con.close()


async def test_run_agent_multiturn_records_agent_turns(monkeypatch, tmp_path):
    """La trace porte les DEUX voix : agent_turn en miroir de human_turn."""
    turns = iter(["mon tour d'agent", "FINI"])

    async def fake_query(*, prompt, options):
        from claude_agent_sdk import AssistantMessage, TextBlock

        yield AssistantMessage(content=[TextBlock(text=next(turns))], model="m")

    monkeypatch.setattr("intreepid.agent.orchestrator.query", fake_query)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    db = tmp_path / "cur.duckdb"
    prof = _script_profile(replies=["ma réponse humaine"], sink=[])
    await run_agent(prof, "start", trace_to=db)

    from intreepid.scribe.store import load

    tr = load(db, _only_session(db))
    agents = [n for n in tr.nodes if n.kind == "agent_turn"]
    assert len(agents) == 2, "un agent_turn par tour, y compris le tour terminal"
    assert agents[0].content["text"] == "mon tour d'agent"
    assert agents[0].meta["actor"] == "agent"
    # le tour de l'agent précède la réponse humaine qu'il provoque
    humain = next(n for n in tr.nodes if n.kind == "human_turn")
    assert agents[0].seq < humain.seq


async def test_run_agent_oneshot_nenregistre_pas_agent_turn(monkeypatch, tmp_path):
    """En one-shot, le texte est projeté par on_result : pas de agent_turn."""

    async def fake_query(*, prompt, options):
        yield AssistantMessage(content=[TextBlock(text="v")], model="m")

    monkeypatch.setattr("intreepid.agent.orchestrator.query", fake_query)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    db = tmp_path / "one.duckdb"
    await run_agent(_text_profile(), "hi", trace_to=db)

    from intreepid.scribe.store import load

    tr = load(db, _only_session(db))
    assert [n.kind for n in tr.nodes if n.kind == "agent_turn"] == []


async def test_thinking_est_transmis_tel_quel_sans_deriver_de_la_trace(
    monkeypatch, tmp_path
):
    """Le socle ne décide pas du thinking : il transmet ce qu'on lui donne.

    Sans ça, tracer une session change ce qu'elle coûte (effet d'observateur) :
    le thinking étendu s'activait du seul fait de la présence du greffier.
    """
    vus: list[bool] = []

    async def fake_query(*, prompt, options):
        yield AssistantMessage(content=[TextBlock(text="v")], model="m")

    def _build_options(model, thinking):
        vus.append(thinking)
        return ClaudeAgentOptions()

    monkeypatch.setattr("intreepid.agent.orchestrator.query", fake_query)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    prof = Profile(
        role="test",
        build_options=_build_options,
        parse=lambda chunks: "\n".join(chunks),
    )

    # tracé mais thinking non demandé => False (aujourd'hui : True)
    await run_agent(prof, "hi", trace_to=tmp_path / "a.duckdb")
    # non tracé mais thinking demandé => True (aujourd'hui : False)
    await run_agent(prof, "hi", thinking=True)

    assert vus == [False, True]


async def test_agent_turn_survit_a_une_interruption_humaine(monkeypatch, tmp_path):
    """Ctrl+C pendant l'attente humaine ne doit pas perdre le tour de l'agent."""

    async def fake_query(*, prompt, options):
        from claude_agent_sdk import AssistantMessage, TextBlock

        yield AssistantMessage(content=[TextBlock(text="tour ecrit")], model="m")

    monkeypatch.setattr("intreepid.agent.orchestrator.query", fake_query)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def _next_input_qui_interrompt(result):
        raise KeyboardInterrupt

    prof = Profile(
        role="curator-fake",
        build_options=lambda model, thinking: ClaudeAgentOptions(),
        parse=lambda chunks: "\n".join(chunks),
        next_input=_next_input_qui_interrompt,
        build_prompt=lambda transcript: "x",
    )
    db = tmp_path / "abort.duckdb"
    with pytest.raises(KeyboardInterrupt):
        await run_agent(prof, "start", trace_to=db)

    from intreepid.scribe.store import load

    tr = load(db, _only_session(db))
    agents = [n for n in tr.nodes if n.kind == "agent_turn"]
    assert len(agents) == 1
    assert agents[0].content["text"] == "tour ecrit"
    assert tr.status == "aborted"
