from __future__ import annotations

from typing import cast, List

from PySide2.QtWidgets import QApplication

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
        m = cast(int, pn.evaluate("m"))
        assertEquals(2, m)
        return None

    hlp.defineSentence("My birthday is in {m:month}.", Evaluator(evaluate))

    root = hlp.parse("My birthday is in March.", None)
    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    root.evaluate()

    autocompletions = []
    hlp.parse("My birthday is in ", autocompletions)
    print("autocompletions = " + str([a.completion for a in autocompletions]))


def interactive():
    hlp = Parser()
    hlp.defineSentence("My birthday is in {m:month}.", None)

    app = QApplication([])
    te = ACEditor(hlp)
    te.show()
    exit(app.exec_())


if __name__ == "__main__":
    # test01()
    interactive()
