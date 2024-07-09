from __future__ import annotations

import os.path
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
    homefolder: str = os.path.expanduser('~')
    print(homefolder)
    hlp = Parser()

    def evaluate(pn: ParsedNode) -> object:
        d = cast(str, pn.evaluate("d"))
        assertEquals(homefolder, d)
        return None

    hlp.defineSentence("My home folder is {d:path}.", Evaluator(evaluate))

    root = hlp.parse("My home folder is '" + homefolder + "'.", None)
    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    root.evaluate()


def interactive():
    homefolder: str = os.path.expanduser('~')
    print(homefolder)
    hlp = Parser()
    hlp.defineSentence("My home folder is {d:path}.", None)
    hlp.compile()

    app = QApplication([])
    te = ACEditor(hlp)
    te.show()
    exit(app.exec_())


if __name__ == "__main__":
    # test01()
    interactive()
