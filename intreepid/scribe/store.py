"""Persistance de l'arbre de session en DuckDB (store épisodique dédié, immuable).

``Scribe`` : context manager qui ouvre une connexion write vers un fichier DuckDB
distinct des sources (P3), insère chaque nœud de façon incrémentale (durable dès
la capture) et scelle la session en sortie — ``closed`` en sortie normale,
``aborted`` + raison sur exception/interruption. ``load`` réhydrate un arbre (P4).
Le temps est stocké en **UTC naïf** et rendu *aware* par ``load`` (cf. ``_now``).
Append-only : une session déjà présente n'est jamais réécrite.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from intreepid.scribe.trace import SessionTrace, TraceBuilder, TraceNode

logger = logging.getLogger(__name__)

_SESSIONS_DDL = (
    "CREATE TABLE IF NOT EXISTS sessions (session_id VARCHAR PRIMARY KEY, "
    "question VARCHAR, model VARCHAR, started_at TIMESTAMP, ended_at TIMESTAMP, "
    "status VARCHAR, meta VARCHAR)"
)
_NODES_DDL = (
    "CREATE TABLE IF NOT EXISTS nodes (id VARCHAR PRIMARY KEY, session_id VARCHAR, "
    "seq INTEGER, parent_id VARCHAR, kind VARCHAR, content VARCHAR, meta VARCHAR, "
    "ts TIMESTAMP)"
)


def _now() -> datetime:
    """Instant courant en UTC **naïf** — la convention de stockage de la trace.

    La colonne est typée ``TIMESTAMP`` (sans fuseau) : un datetime *aware* y
    serait converti vers le fuseau de session PUIS dépouillé, donc la base
    porterait de l'heure locale et les écarts d'une session à cheval sur un
    changement d'heure seraient faux. On écrit donc de l'UTC naïf ; ``load``
    rattache le fuseau à la relecture. (``TIMESTAMPTZ`` a été écarté : le client
    Python de DuckDB exige ``pytz`` pour le relire.)
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Scribe:
    """Enregistreur append-only d'une session, scellé à la sortie du context manager."""

    def __init__(
        self,
        db_path: str | Path,
        session_id: str,
        question: str,
        model: str | None = None,
    ) -> None:
        self._path = Path(db_path)
        self._sid = session_id
        self._builder = TraceBuilder(session_id, question, model)
        self._con: duckdb.DuckDBPyConnection | None = None

    def __enter__(self) -> "Scribe":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._con = duckdb.connect(str(self._path))
        try:
            self._con.execute(_SESSIONS_DDL)
            self._con.execute(_NODES_DDL)
            exists = self._con.execute(
                "SELECT 1 FROM sessions WHERE session_id = ?", [self._sid]
            ).fetchone()
            if exists is not None:
                raise ValueError(f"session déjà présente (immuable) : {self._sid}")
            root = self._builder.root
            self._con.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    self._sid,
                    root.content["question"],
                    root.content["model"],
                    _now(),
                    None,
                    "open",
                    json.dumps({}),
                ],
            )
            self._insert([root])
        except Exception:
            self._con.close()
            self._con = None
            raise
        return self

    def _insert(self, nodes: list[TraceNode]) -> None:
        if self._con is None:
            raise RuntimeError("Scribe utilisé hors de son context manager")
        for n in nodes:
            self._con.execute(
                "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    n.id,
                    n.session_id,
                    n.seq,
                    n.parent_id,
                    n.kind,
                    json.dumps(n.content, ensure_ascii=False, default=str),
                    json.dumps(n.meta, ensure_ascii=False, default=str),
                    _now(),
                ],
            )

    def record(self, message: Any) -> None:
        """Capte un message du flux (peut être appelé pour tout type de message)."""
        self._insert(self._builder.add(message))

    def record_nodes(self, specs: list[tuple[str, Any, Any]]) -> None:
        """Capte des nœuds projetés par le rôle (specs ``(kind, content, meta)``).

        Primitive générique : le socle n'interprète pas le vocabulaire de ``kind``.
        """
        self._insert(self._builder.custom(specs))

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        try:
            status = "aborted" if exc_type is not None else "closed"
            meta = dict(self._builder.result_meta)
            if exc is not None:
                meta["aborted_reason"] = repr(exc)
            if self._con is not None:
                self._con.execute(
                    "UPDATE sessions SET ended_at = ?, status = ?, meta = ? "
                    "WHERE session_id = ?",
                    [
                        _now(),
                        status,
                        json.dumps(meta, ensure_ascii=False, default=str),
                        self._sid,
                    ],
                )
        except Exception:
            logger.exception("greffier : échec du scellement de session %s", self._sid)
        finally:
            if self._con is not None:
                self._con.close()
                self._con = None
        return False  # ne jamais supprimer l'exception de l'agent


def load(db_path: str | Path, session_id: str) -> SessionTrace:
    """Réhydrate un arbre de session depuis le store (P4, lecture read-only).

    Les ``ts`` sont rendus *aware* en UTC. Réserve sur les traces **antérieures**
    à ce correctif : leur base porte de l'heure locale, donc elles seront
    étiquetées UTC à tort — les écarts internes restent justes, seul
    l'horodatage absolu est décalé du fuseau.
    """
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        srow = con.execute(
            "SELECT question, model, status, meta FROM sessions WHERE session_id = ?",
            [session_id],
        ).fetchone()
        if srow is None:
            raise KeyError(session_id)
        nrows = con.execute(
            "SELECT id, session_id, seq, parent_id, kind, content, meta, ts FROM nodes "
            "WHERE session_id = ? ORDER BY seq",
            [session_id],
        ).fetchall()
    finally:
        con.close()
    nodes = [
        TraceNode(
            id=r[0],
            session_id=r[1],
            seq=r[2],
            parent_id=r[3],
            kind=r[4],
            content=json.loads(r[5]),
            meta=json.loads(r[6]),
            # la base porte de l'UTC naïf (cf. _now) : on rend un datetime aware,
            # comparable sans piège aux datetime aware du reste du code
            ts=r[7].replace(tzinfo=timezone.utc) if r[7] is not None else None,
        )
        for r in nrows
    ]
    return SessionTrace(
        session_id=session_id,
        question=srow[0],
        model=srow[1],
        status=srow[2],
        nodes=nodes,
        meta=json.loads(srow[3]) if srow[3] else {},
    )
