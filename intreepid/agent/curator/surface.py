"""Surface REPL du curateur : afficher un tour, lire la réponse humaine (D4).

I/O injectés (writer/reader) => testable sans terminal. L'attente humaine ne
consomme aucun compute (le process est simplement bloqué sur `reader`).
"""

from collections.abc import Callable


class Surface:
    def __init__(
        self,
        writer: Callable[[str], None] = print,
        reader: Callable[[str], str] = input,
    ) -> None:
        self._writer = writer
        self._reader = reader

    def show(self, text: str) -> None:
        self._writer(text)

    def ask(self, prompt: str = "> ") -> str:
        return self._reader(prompt)
