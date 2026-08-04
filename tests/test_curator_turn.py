"""Vérifie le parsing tolérant du tour curateur (bloc fencé, dernier gagne)."""

from intreepid.agent.curator.turn import CuratorTurn, parse_curator_turn


def test_parse_full_block() -> None:
    text = (
        "Voici mon analyse.\n\n"
        "```json\n"
        '{"message": "La colonne vitesse contient 999.",'
        ' "fiche_draft": {"dataset": "d", "columns": {"v": {"type": "categorical"}}},'
        ' "proposes_completion": false}\n'
        "```\n"
    )
    turn: CuratorTurn = parse_curator_turn(text)
    assert turn.message == "La colonne vitesse contient 999."
    assert turn.fiche_draft is not None
    assert turn.fiche_draft["dataset"] == "d"
    assert turn.proposes_completion is False


def test_parse_takes_last_block_not_first():
    text = (
        "```json\n"
        '{"message": "exemple à ignorer", "fiche_draft": null,'
        ' "proposes_completion": false}\n'
        "```\n"
        "puis le vrai tour :\n"
        "```json\n"
        '{"message": "réponse finale", "fiche_draft": null,'
        ' "proposes_completion": true}\n'
        "```\n"
    )
    turn = parse_curator_turn(text)
    assert turn.message == "réponse finale"
    assert turn.proposes_completion is True


def test_parse_no_block_falls_back_to_message():
    turn = parse_curator_turn("juste du texte libre")
    assert turn.message == "juste du texte libre"
    assert turn.fiche_draft is None
    assert turn.proposes_completion is False


def test_parse_missing_fields_defaults():
    text = '```json\n{"message": "m"}\n```\n'
    turn = parse_curator_turn(text)
    assert turn.fiche_draft is None
    assert turn.proposes_completion is False


def test_parse_non_json_block_falls_back():
    text = "```\ncolonnes:\n  a: numeric  # pas du JSON\n```\n"
    turn = parse_curator_turn(text)
    assert turn.fiche_draft is None
    assert turn.proposes_completion is False
    assert "colonnes" in turn.message  # repli sur le texte brut
