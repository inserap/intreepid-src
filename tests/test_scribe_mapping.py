"""Vérifie le mapping PUR flux Agent SDK → nœuds de trace (déterministe, sans I/O)."""

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from intreepid.scribe.trace import TraceBuilder


def test_root_is_first_node():
    b = TraceBuilder("s1", "ma question", "opus")
    assert b.root.kind == "session_root"
    assert b.root.seq == 0
    assert b.root.parent_id is None
    assert b.root.content == {"question": "ma question", "model": "opus"}


def test_assistant_thinking_and_tool_call():
    b = TraceBuilder("s1", "q", "opus")
    msg = AssistantMessage(
        content=[
            ThinkingBlock(thinking="je pose une hypothèse", signature="sig"),
            ToolUseBlock(id="t1", name="mcp__x__profile_stats", input={"table": "z"}),
        ],
        model="opus",
    )
    nodes = b.add(msg)
    assert [n.kind for n in nodes] == ["thinking", "tool_call"]
    assert nodes[0].content == {"text": "je pose une hypothèse"}
    assert nodes[1].content == {
        "name": "mcp__x__profile_stats",
        "input": {"table": "z"},
    }
    assert nodes[1].meta["tool_use_id"] == "t1"
    assert all(n.parent_id == b.root.id for n in nodes)


def test_tool_result_parented_to_its_call():
    b = TraceBuilder("s1", "q", "opus")
    call_nodes = b.add(
        AssistantMessage(
            content=[ToolUseBlock(id="t1", name="n", input={})], model="opus"
        )
    )
    call = call_nodes[0]
    result_nodes = b.add(
        UserMessage(content=[ToolResultBlock(tool_use_id="t1", content="agrégat")])
    )
    assert len(result_nodes) == 1
    r = result_nodes[0]
    assert r.kind == "tool_result"
    assert r.parent_id == call.id
    assert r.content["content"] == "agrégat"
    assert r.content["is_error"] is None


def test_custom_makes_arbitrary_nodes():
    b = TraceBuilder("s1", "q", "opus")
    nodes = b.custom(
        [
            ("note", {"text": "libre"}, {"tag": "x"}),
            ("marker", {}, {}),
        ]
    )
    assert [n.kind for n in nodes] == ["note", "marker"]
    assert nodes[0].content == {"text": "libre"}
    assert nodes[0].meta == {"tag": "x"}
    assert all(n.parent_id == b.root.id for n in nodes)


def test_result_message_remplit_meta_et_cree_un_noeud():
    b = TraceBuilder("s1", "q", "opus")
    nodes = b.add(
        ResultMessage(
            subtype="success",
            duration_ms=120_000,
            duration_api_ms=90_000,
            is_error=False,
            num_turns=3,
            session_id="s1",
            total_cost_usd=0.02,
            usage={"input_tokens": 1000, "output_tokens": 500},
            terminal_reason="completed",
        )
    )
    # la méta de session garde son comportement (elle alimente le notebook)
    assert b.result_meta["num_turns"] == 3
    assert b.result_meta["total_cost_usd"] == 0.02
    assert b.result_meta["terminal_reason"] == "completed"
    # et la fin de tour devient un nœud durable, mesurable tour par tour
    assert len(nodes) == 1
    node = nodes[0]
    assert node.kind == "turn_result"
    assert node.parent_id == b.root.id
    assert node.content["duration_ms"] == 120_000
    assert node.content["duration_api_ms"] == 90_000
    assert node.content["total_cost_usd"] == 0.02
    assert node.content["usage"]["output_tokens"] == 500
    assert node.content["terminal_reason"] == "completed"
    assert node.meta == {}  # le socle n'attribue rien (agnostique du rôle)


def test_tracenode_ts_vaut_none_a_la_capture():
    b = TraceBuilder("s1", "q", None)
    assert b.root.ts is None  # le builder est pur : le store est l'autorité du temps


def test_seq_is_monotonic_and_ids_deterministic():
    b = TraceBuilder("s1", "q", "opus")
    b.add(
        AssistantMessage(
            content=[ToolUseBlock(id="t1", name="n", input={})], model="opus"
        )
    )
    ids = [n.id for n in b.custom([("note", {"x": 1}, {})])]
    assert b.root.id == "s1#0"
    assert ids == ["s1#2"]  # root=0, tool_call=1, custom=2
