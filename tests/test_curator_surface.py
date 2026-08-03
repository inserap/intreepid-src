"""Vérifie la surface REPL avec I/O injectés (déterministe, sans terminal)."""

from intreepid.agent.curator.surface import Surface


def test_surface_show_and_ask():
    shown: list[str] = []
    answers = iter(["réponse 1", "réponse 2"])
    s = Surface(writer=shown.append, reader=lambda _prompt: next(answers))
    s.show("bonjour")
    assert s.ask() == "réponse 1"
    assert s.ask() == "réponse 2"
    assert shown == ["bonjour"]
