from __future__ import annotations

from typing import List, cast

from nlScript.core.bnf import BNF
from nlScript.core.lexer import Lexer
from nlScript.core.parsingstate import ParsingState
from nlScript.core.rdparser import RDParser
from nlScript.core.terminal import DIGIT, LETTER
from nlScript.ebnf import ebnfparsednodefactory
from nlScript.ebnf.ebnfcore import EBNFCore
from nlScript.core import graphviz
from nlScript.parsednode import ParsedNode
from nlScript.parseexception import ParseException


def assertEquals(exp, real):
    if exp != real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def assertNotEquals(exp, real):
    if exp == real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def makeGrammar(lower: int, upper: int) -> BNF:
    grammar = EBNFCore()
    rule = grammar.repeat(
        "repeat",
        grammar.sequence("seq", [
                DIGIT.withName(),
                LETTER.withName()
        ]).withName("seq"),
        rfrom=lower,
        rto=upper)
    grammar.compile(rule.tgt)
    return grammar.getBNF()


def testSuccess(grammar: BNF, input: str):
    lexer = Lexer(input)
    parser = RDParser(grammar, lexer, ebnfparsednodefactory.INSTANCE)
    root = parser.parse()
    print(graphviz.toVizDotLink(root))

    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)

    parsed: ParsedNode = root.children[0]
    assertEquals(len(input) // 2, parsed.numChildren())

    idx = 0
    for child in parsed.children:
        assertEquals(input[idx:idx+2], child.getParsedString())
        assertEquals(2, child.numChildren())
        idx += 2

    # test evaluate
    evaluated = cast(List, parsed.evaluateSelf())
    for idx, ev in enumerate(evaluated):
        assertEquals(input[2 * idx: 2 * idx + 2], ev)

    # test names
    for child in parsed.children:
        assertEquals("seq", child.name)


def testFailure(grammar: BNF, input: str):
    lexer = Lexer(input)
    parser = RDParser(grammar, lexer, ebnfparsednodefactory.INSTANCE)
    try:
        root = parser.parse()
        assertNotEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    except ParseException:
        pass


def test1():
    print("test1")
    g = makeGrammar(1, 1)
    testSuccess(g, "1a")
    testFailure(g, "")
    testFailure(g, "1a1a")
    testFailure(g, "s")


def test2():
    print("test2")
    g = makeGrammar(0, 1)
    testSuccess(g, "1a")
    testSuccess(g, "")
    testFailure(g, "1a1a")
    testFailure(g, "s")


def test3():
    print("test3")
    g = makeGrammar(0, 0)
    testFailure(g, "1a")
    testSuccess(g, "")
    testFailure(g, "1a1a")
    testFailure(g, "s")


def test4():
    print("test4")
    g = makeGrammar(1, 3)
    testFailure(g, "")
    testSuccess(g, "1a")
    testSuccess(g, "1a2a")
    testSuccess(g, "1a2a3a")
    testFailure(g, "1a2a3a4a")
    testFailure(g, "s")


def test5():
    print("test5")
    g = makeGrammar(0, 3)
    testSuccess(g, "")
    testSuccess(g, "1a")
    testSuccess(g, "1a2a")
    testSuccess(g, "1a2a3a")
    testFailure(g, "1a2a3a4a")
    testFailure(g, "s")


if __name__ == "__main__":
    test1()
    test2()
    test3()
    test4()
    test5()
