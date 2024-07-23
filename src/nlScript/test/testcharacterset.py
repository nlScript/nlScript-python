from __future__ import annotations

from typing import cast, List

from nlScript.core.parsingstate import ParsingState
from nlScript.evaluator import Evaluator
from nlScript.parsednode import ParsedNode
from nlScript.parser import Parser


def assertEquals(exp, real):
    if exp != real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def assertArrayEquals(exp: List[object], real: List[object]):
    if len(exp) != len(real):
        raise Exception("Expected " + str(exp) + ", but got " + str(real))

    if any(map(lambda x, y: x != y, exp, real)):
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def test01():
    hlp = Parser()

    def evaluate1(pn: ParsedNode) -> object:
        d = cast(str, pn.evaluate("c"))
        assertEquals("f", d)
        return None

    hlp.defineSentence("An arbitrary alphanumeric character: {c:[a-zA-Z0-9]}.", evaluate1)

    def evaluate2(pn: ParsedNode) -> object:
        d = cast(List[object], pn.evaluate("c"))
        assertArrayEquals("f1", d)
        return None

    hlp.defineSentence("Two arbitrary alphanumeric characters: {c:[a-zA-Z0-9]:2}.", evaluate2)

    root = hlp.parse("An arbitrary alphanumeric character: f.", None)
    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    root.evaluate()

    root = hlp.parse("Two arbitrary alphanumeric characters: f1.", None)
    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    root.evaluate()


if __name__ == "__main__":
    test01()
