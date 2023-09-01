from __future__ import annotations


class Autocompletion:
    def __init__(self, completion: str, alreadyEnteredText: str):
        self._completion = completion
        self._alreadyEnteredText = alreadyEnteredText

    @property
    def completion(self) -> str:
        return self._completion

    @property
    def alreadyEnteredText(self) -> str:
        return self._alreadyEnteredText

    def __eq__(self, other: Autocompletion) -> bool:
        if type(self) == type(other):
            return self._completion == other.completion
        return False

    def __ne__(self, other: Autocompletion) -> bool:
        return not self == other

    def __hash__(self) -> object:
        return hash(self._completion)
    
    def __str__(self) -> str:
        return self._completion
