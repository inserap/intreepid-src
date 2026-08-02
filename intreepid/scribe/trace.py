"""Modèle de trace de session (arbre immuable) et mapping du flux Agent SDK.

Contrat de données du greffier : convertit le flux de messages de l'agent en
nœuds typés. Logique PURE (aucun I/O, aucun appel LLM) donc testable avec des
messages factices. La persistance vit dans ``store.py``.
"""

from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)


@dataclass
class TraceNode:
    """Un nœud de l'arbre de session (grain événement, kind typé)."""

    id: str
    session_id: str
    seq: int
    parent_id: str | None
    kind: str
    content: dict[str, Any]
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionTrace:
    """Un arbre de session réhydraté (résultat de ``store.load``)."""

    session_id: str
    question: str
    model: str | None
    status: str
    nodes: list[TraceNode]
    meta: dict[str, Any] = field(default_factory=dict)


class TraceBuilder:
    """Construit l'arbre à partir du flux de messages (pur, déterministe).

    Ids déterministes ``{session_id}#{seq}`` (pas d'uuid → testable). Apparie
    chaque ``tool_result`` à son ``tool_call`` via ``tool_use_id``.
    """

    def __init__(self, session_id: str, question: str, model: str | None) -> None:
        self.session_id = session_id
        self._seq = 0
        self._call_node: dict[str, str] = {}
        self.result_meta: dict[str, Any] = {}
        self.root = self._node(
            "session_root", {"question": question, "model": model}, parent_id=None
        )

    def _node(
        self,
        kind: str,
        content: dict[str, Any],
        parent_id: str | None,
        meta: dict[str, Any] | None = None,
    ) -> TraceNode:
        node = TraceNode(
            id=f"{self.session_id}#{self._seq}",
            session_id=self.session_id,
            seq=self._seq,
            parent_id=parent_id,
            kind=kind,
            content=content,
            meta=meta or {},
        )
        self._seq += 1
        return node

    def add(self, message: object) -> list[TraceNode]:
        """Mappe un message du flux en 0..N nœuds.

        Enfants de la racine, sauf tool_result.
        """
        out: list[TraceNode] = []
        if isinstance(message, AssistantMessage):
            # ThinkingBlock/ToolUseBlock = ACTES de l'agent ; TextBlock = RÉSULTAT,
            # projeté en nœuds par le profil (Profile.on_result) ;
            # ServerToolUseBlock/ServerToolResultBlock hors périmètre.
            for block in message.content:
                if isinstance(block, ThinkingBlock):
                    out.append(
                        self._node("thinking", {"text": block.thinking}, self.root.id)
                    )
                elif isinstance(block, ToolUseBlock):
                    node = self._node(
                        "tool_call",
                        {"name": block.name, "input": block.input},
                        self.root.id,
                        {"tool_use_id": block.id},
                    )
                    self._call_node[block.id] = node.id
                    out.append(node)
        elif isinstance(message, UserMessage):
            if isinstance(message.content, list):
                for block in message.content:
                    if isinstance(block, ToolResultBlock):
                        parent = self._call_node.get(block.tool_use_id, self.root.id)
                        out.append(
                            self._node(
                                "tool_result",
                                {"content": block.content, "is_error": block.is_error},
                                parent,
                                {"tool_use_id": block.tool_use_id},
                            )
                        )
        elif isinstance(message, ResultMessage):
            self.result_meta = {
                "num_turns": message.num_turns,
                "total_cost_usd": message.total_cost_usd,
                "terminal_reason": message.terminal_reason,
            }
        return out

    def custom(
        self, specs: list[tuple[str, dict[str, Any], dict[str, Any]]]
    ) -> list[TraceNode]:
        """Crée un nœud par spec ``(kind, content, meta)``, enfant de la racine.

        Primitive générique : le vocabulaire de ``kind`` et le schéma de
        ``content``/``meta`` sont décidés par le rôle appelant (profil), pas par
        le socle. Cf. ADR-0009 (le socle greffier est agnostique du rôle).
        """
        return [
            self._node(kind, content, self.root.id, meta)
            for (kind, content, meta) in specs
        ]
