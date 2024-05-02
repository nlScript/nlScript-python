from __future__ import annotations

import datetime
from typing import cast, List

from PyQt5.QtWidgets import QApplication

from nls.core.parsingstate import ParsingState
from nls.evaluator import Evaluator
from nls.parsednode import ParsedNode
from nls.parser import Parser
from nls.ui.ui import ACEditor


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
        m = cast(datetime.datetime, pn.evaluate("d"))
        assertEquals(datetime.datetime(2020, 9, 12, 8, 0), m)
        return None

    hlp.defineSentence("My daughter's school started {d:date-time}.", Evaluator(evaluate))

    root = hlp.parse("My daughter's school started 12 September 2020 8:00.", None)
    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    root.evaluate()


def interactive():
    hlp = Parser()

    hlp.defineSentence("My daughter's school started {d:date-time}.", None)

    app = QApplication([])
    te = ACEditor(hlp)
    te.show()
    exit(app.exec_())


if __name__ == "__main__":
    test01()
    interactive()
