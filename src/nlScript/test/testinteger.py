from __future__ import annotations

from typing import cast, List

from nlScript.core.autocompletion import Autocompletion
from nlScript.core.parsingstate import ParsingState
from nlScript.evaluator import Evaluator
from nlScript.parsednode import ParsedNode
from nlScript.parser import Parser


def test01():
    hlp = Parser()

    def evaluate(pn: ParsedNode) -> object:
        p = cast(int, pn.evaluate("p"))
        assertEquals(35, p)
        return None

    hlp.defineSentence("Now there are only {p:int}% left.", evaluate)

    autocompletions: List[Autocompletion] = []
    root = hlp.parse("Now there are only 5", autocompletions)
    assertEquals(ParsingState.END_OF_INPUT, root.matcher.state)
    assertEquals(0, len(autocompletions))

    root = hlp.parse("Now there are only 35% left.", autocompletions)
    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    root.evaluate()


def assertEquals(exp, real):
    if exp != real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def assertNotEquals(exp, real):
    if exp == real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


if __name__ == "__main__":
    test01()
