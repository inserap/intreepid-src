"""Éval bout-en-bout du greffier avec le vrai agent (marqué `agent`, lent, réseau).

Vérifie qu'une session réelle produit un arbre non vide, scellé, avec au moins un
appel MCP et une observation. Le thinking est best-effort (peut être absent).
"""

import duckdb
import pytest

from intreepid.agent.runner import run_analysis
from intreepid.scribe.store import load

pytestmark = pytest.mark.agent

QUESTION = "Profile les colonnes du dataset accidents_route et rends ton verdict."


async def test_real_session_is_captured(tmp_path):
    db = tmp_path / "ep.duckdb"
    verdict = await run_analysis(QUESTION, trace_to=db)
    assert verdict  # l'analyste a rendu au moins une observation

    con = duckdb.connect(str(db), read_only=True)
    try:
        row = con.execute("SELECT session_id FROM sessions").fetchone()
    finally:
        con.close()
    assert row is not None, "aucune session enregistrée dans le store"
    sid = row[0]
    tr = load(db, sid)
    assert tr.status == "closed"
    assert any(n.kind == "tool_call" for n in tr.nodes)
    assert any(n.kind == "observation" for n in tr.nodes)
