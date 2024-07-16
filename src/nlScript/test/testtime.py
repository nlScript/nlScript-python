from __future__ import annotations

import datetime
from typing import cast

from PySide2.QtWidgets import QApplication

from nlScript.core.parsingstate import ParsingState
from nlScript.evaluator import Evaluator
from nlScript.parsednode import ParsedNode
from nlScript.parser import Parser
from nlScript.ui.ui import ACEditor


def test01():
    hlp = Parser()

    def evaluate(pn: ParsedNode) -> object:
        p = cast(datetime.time, pn.evaluate("t"))
        assertEquals(20, p.hour)
        assertEquals(30, p.minute)
        return None

    hlp.defineSentence("The pizza comes at {t:time}.", Evaluator(evaluate))

    root = hlp.parse("The pizza comes at 20:30.", None)
    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    root.evaluate()


def interactive():
    hlp = Parser()
    hlp.defineSentence("The pizza comes at {t:time}.", None)
    app = QApplication([])
    te = ACEditor(hlp)
    te.show()
    exit(app.exec_())


def assertEquals(exp, real):
    if exp != real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def assertNotEquals(exp, real):
    if exp == real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


if __name__ == "__main__":
    test01()
    interactive()
