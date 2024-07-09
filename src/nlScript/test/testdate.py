from __future__ import annotations

import datetime
from typing import cast, List

from PyQt5.QtWidgets import QApplication

from nlScript.core.parsingstate import ParsingState
from nlScript.evaluator import Evaluator
from nlScript.parsednode import ParsedNode
from nlScript.parser import Parser
from nlScript.ui.ui import ACEditor


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

    def evaluate(pn: ParsedNode) -> object:
        m = cast(datetime.date, pn.evaluate("d"))
        assertEquals(datetime.date(2020, 10, 3), m)
        return None

    hlp.defineSentence("My cat was born on {d:date}.", Evaluator(evaluate))

    root = hlp.parse("My cat was born on 03 October 2020.", None)
    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    root.evaluate()


def interactive():
    hlp = Parser()

    hlp.defineSentence("My cat was born on {d:date}.", None)

    app = QApplication([])
    te = ACEditor(hlp)
    te.show()
    exit(app.exec_())


if __name__ == "__main__":
    # test01()
    interactive()
