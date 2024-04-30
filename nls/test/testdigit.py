from __future__ import annotations

from typing import cast, List

from nls.core.parsingstate import ParsingState
from nls.evaluator import Evaluator
from nls.parsednode import ParsedNode
from nls.parser import Parser


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
        d = cast(str, pn.evaluate("d"))
        assertEquals("0", d)
        return None

    hlp.defineSentence("The first digit of my telephone number is {d:digit}.", Evaluator(evaluate1))

    def evaluate2(pn: ParsedNode) -> object:
        d = cast(List[object], pn.evaluate("d"))
        assertArrayEquals(["0", "9"], d)
        return None

    hlp.defineSentence("The first two digits of my telephone number are {d:digit:2}.", Evaluator(evaluate2))

    root = hlp.parse("The first digit of my telephone number is 0.", None)
    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    root.evaluate()

    root = hlp.parse("The first two digits of my telephone number are 09.", None)
    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    root.evaluate()


if __name__ == "__main__":
    test01()
