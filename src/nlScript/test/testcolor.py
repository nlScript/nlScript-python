from __future__ import annotations

from typing import cast

from PySide2.QtWidgets import QApplication

from nlScript.core.autocompletion import Purpose
from nlScript.core.parsingstate import ParsingState
from nlScript.evaluator import Evaluator
from nlScript.parsednode import ParsedNode
from nlScript.parser import Parser


def test01():
    hlp = Parser()

    def evaluate(pn: ParsedNode) -> object:
        color = cast(int, pn.evaluate("text-color"))
        blue = color & 255
        green = (color >> 8) & 255
        red = (color >> 16) & 255
        assertEquals(128, red)
        assertEquals(255, green)
        assertEquals(0, blue)
        return None

    hlp.defineSentence("My favorite color is {text-color:color}.", Evaluator(evaluate))

    autocompletions = []
    root = hlp.parse("My favorite color is ", autocompletions)
    actual = list(map(lambda a: a.getCompletion(Purpose.FOR_INSERTION), autocompletions))
    expected = [
        "(${red}, ${green}, ${blue})",
        "black",
        "white",
        "red",
        "orange",
        "yellow",
        "lawn green",
        "green",
        "spring green",
        "cyan",
        "azure",
        "blue",
        "violet",
        "magenta",
        "pink",
        "gray"]
    assertEquals(expected, actual)

    root = hlp.parse("My favorite color is lawn green.", None)
    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    root.evaluate()


def assertEquals(exp, real):
    if exp != real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def assertNotEquals(exp, real):
    if exp == real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


if __name__ == "__main__":
    # test01()
    hlp = Parser()
    hlp.defineSentence("My favorite color is {c:color}.")
    # hlp.defineSentence("My favorite color is {c:int}.", Evaluator(lambda pn: None))
    hlp.compile()
    from nlScript.ui.ui import ACEditor

    app = QApplication([])
    te = ACEditor(parser=hlp)
    te.show()
    exit(app.exec_())
