"""Vérifie le mapping PUR flux Agent SDK → nœuds de trace (déterministe, sans I/O)."""

from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from intreepid.scribe.trace import TraceBuilder


@dataclass
class _Observation:
    """Test helper: observation object for verdict testing."""

    claim: str
    statut: str
    note: Any = None
    confiance: Any = None
    nature: Any = None


def _obs(
    claim: str, statut: str, note: Any = None, confiance: Any = None, nature: Any = None
) -> _Observation:
    """Create a test observation object."""
    return _Observation(
        claim=claim, statut=statut, note=note, confiance=confiance, nature=nature
    )


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


def test_verdict_makes_observation_nodes():
    b = TraceBuilder("s1", "q", "opus")
    nodes = b.verdict(
        [
            _obs("BE point noir", "fait", "z=+34", "haute"),
            _obs("baisse⇒sûr", "refusé", "causalité"),
        ]
    )
    assert [n.kind for n in nodes] == ["observation", "observation"]
    assert nodes[0].content == {"claim": "BE point noir", "note": "z=+34"}
    assert nodes[0].meta == {"statut": "fait", "confiance": "haute", "nature": None}
    assert nodes[1].meta["statut"] == "refusé"  # branche morte documentée
    assert all(n.parent_id == b.root.id for n in nodes)


def test_result_message_fills_result_meta_no_node():
    b = TraceBuilder("s1", "q", "opus")
    nodes = b.add(
        ResultMessage(
            subtype="success",
            duration_ms=10,
            duration_api_ms=8,
            is_error=False,
            num_turns=3,
            session_id="x",
            total_cost_usd=0.02,
            terminal_reason="completed",
        )
    )
    assert nodes == []
    assert b.result_meta["num_turns"] == 3
    assert b.result_meta["terminal_reason"] == "completed"


def test_seq_is_monotonic_and_ids_deterministic():
    b = TraceBuilder("s1", "q", "opus")
    b.add(
        AssistantMessage(
            content=[ToolUseBlock(id="t1", name="n", input={})], model="opus"
        )
    )
    ids = [n.id for n in b.verdict([_obs("c", "fait")])]
    assert b.root.id == "s1#0"
    assert ids == ["s1#2"]  # root=0, tool_call=1, observation=2
