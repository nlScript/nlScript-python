from __future__ import annotations

import datetime
from typing import cast

from nls.core.parsingstate import ParsingState
from nls.evaluator import Evaluator
from nls.parsednode import ParsedNode
from nls.parser import Parser


def test01():
    hlp = Parser()

    def evaluate(pn: ParsedNode) -> object:
        p = cast(datetime.time, pn.evaluate("t"))
        assertEquals(9, p.hour)
        assertEquals(30, p.minute)
        return None

    hlp.defineSentence("The pizza comes at {t:time}.", Evaluator(evaluate))

    root = hlp.parse("The pizza comes at 9:30.", None)
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
