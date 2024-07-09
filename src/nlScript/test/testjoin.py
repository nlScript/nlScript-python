from __future__ import annotations

from typing import List, cast

from nlScript.core.bnf import BNF
from nlScript.core.lexer import Lexer
from nlScript.core.parsingstate import ParsingState
from nlScript.core.rdparser import RDParser
from nlScript.core.terminal import DIGIT, literal
from nlScript.ebnf import ebnfparsednodefactory
from nlScript.ebnf.ebnfcore import EBNFCore
from nlScript.core import graphviz
from nlScript.parsednode import ParsedNode
from nlScript.parseexception import ParseException
from nlScript.util.range import Range, PLUS, STAR, OPTIONAL


def testKeepDelimiters():
    grammar = EBNFCore()
    rule = grammar.join("join",
                        DIGIT.withName(),
                        literal("("),
                        literal(")"),
                        literal(","),
                        onlyKeepEntries=False,
                        names=["ha", "ho", "hu"])

    grammar.compile(rule.tgt)

    input = "(1,3,4)"
    lexer = Lexer(input)
    test = RDParser(grammar.getBNF(), lexer, ebnfparsednodefactory.INSTANCE)
    root = test.parse()
    print(graphviz.toVizDotLink(root))

    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)

    parsedJoinNode = root.getChild(0)
    assertEquals(7, parsedJoinNode.numChildren())

    # test names
    assertEquals("open", parsedJoinNode.getChild(0).name)
    assertEquals("ha", parsedJoinNode.getChild(1).name)
    assertEquals("delimiter", parsedJoinNode.getChild(2).name)
    assertEquals("ho", parsedJoinNode.getChild(3).name)
    assertEquals("delimiter", parsedJoinNode.getChild(4).name)
    assertEquals("hu", parsedJoinNode.getChild(5).name)
    assertEquals("close", parsedJoinNode.getChild(6).name)


def assertEquals(exp, real):
    if exp != real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def assertNotEquals(exp, real):
    if exp == real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def makeGrammar(withOpenAndClose: bool, withDelimiter: bool, range: Range) -> BNF:
    grammar = EBNFCore()
    rule = grammar.join(
        "join",
        DIGIT.withName("digit"),
        literal("(") if withOpenAndClose else None,
        literal(")") if withOpenAndClose else None,
        literal(",") if withDelimiter else None,
        cardinality=range)
    grammar.compile(rule.tgt)
    return grammar.getBNF()


def testSuccess(grammar: BNF, input: str, result: List[str]):
    lexer = Lexer(input)
    parser = RDParser(grammar, lexer, ebnfparsednodefactory.INSTANCE)
    root = parser.parse()
    print(graphviz.toVizDotLink(root))

    assertEquals(ParsingState.SUCCESSFUL, root.matcher.state)

    parsed: ParsedNode = root.children[0]
    assertEquals(len(result), parsed.numChildren())
    assertEquals(input, parsed.getParsedString())

    for idx, child in enumerate(parsed.children):
        assertEquals(result[idx], child.getParsedString())
        assertEquals(0, child.numChildren())

    # test evaluate
    evaluated = cast(List, parsed.evaluateSelf())
    for idx, ev in enumerate(evaluated):
        assertEquals(result[idx], ev)

    # test names
    for child in parsed.children:
        assertEquals(DIGIT.symbol, child.name)


def testFailure(grammar: BNF, input: str):
    lexer = Lexer(input)
    parser = RDParser(grammar, lexer, ebnfparsednodefactory.INSTANCE)
    try:
        root = parser.parse()
        assertNotEquals(ParsingState.SUCCESSFUL, root.matcher.state)
    except ParseException:
        pass


def test():
    withOpenClose = [True, True, False, False]
    withDelimiter = [True, False, True, False]
    inputs = [
        [
            "",
            "()",
            "(1)",
            "(1,2)",
            "(1,2,3)",
            "1,2,3",
            "s"
        ],
        [
            "",
            "()",
            "(1)",
            "(12)",
            "(123)",
            "123",
            "s"
        ],
        [
            "()",
            "",
            "1",
            "1,2",
            "1,2,3",
            "(1,2,3)",
            "s"
        ],
        [
            "()",
            "",
            "1",
            "12",
            "123",
            "(123)",
            "s"
        ]

    ]

    for i in range(3):
        grammar = makeGrammar(withOpenClose[i], withDelimiter[i], PLUS)
        testFailure(grammar, inputs[i][0])
        testFailure(grammar, inputs[i][1])
        testSuccess(grammar, inputs[i][2], ["1"])
        testSuccess(grammar, inputs[i][3], ["1", "2"])
        testSuccess(grammar, inputs[i][4], ["1", "2", "3"])
        testFailure(grammar, inputs[i][5])
        testFailure(grammar, inputs[i][6])

        grammar = makeGrammar(withOpenClose[i], withDelimiter[i], STAR)
        testFailure(grammar, inputs[i][0])
        testSuccess(grammar, inputs[i][1], [])
        testSuccess(grammar, inputs[i][2], ["1"])
        testSuccess(grammar, inputs[i][3], ["1", "2"])
        testSuccess(grammar, inputs[i][4], ["1", "2", "3"])
        testFailure(grammar, inputs[i][5])
        testFailure(grammar, inputs[i][6])

        grammar = makeGrammar(withOpenClose[i], withDelimiter[i], OPTIONAL)
        testFailure(grammar, inputs[i][0])
        testSuccess(grammar, inputs[i][1], [])
        testSuccess(grammar, inputs[i][2], ["1"])
        testFailure(grammar, inputs[i][3])
        testFailure(grammar, inputs[i][4])
        testFailure(grammar, inputs[i][5])
        testFailure(grammar, inputs[i][6])

        grammar = makeGrammar(withOpenClose[i], withDelimiter[i], Range(0, 0))
        testFailure(grammar, inputs[i][0])
        testSuccess(grammar, inputs[i][1], [])
        testFailure(grammar, inputs[i][2])
        testFailure(grammar, inputs[i][3])
        testFailure(grammar, inputs[i][4])
        testFailure(grammar, inputs[i][5])
        testFailure(grammar, inputs[i][6])

        grammar = makeGrammar(withOpenClose[i], withDelimiter[i], Range(1, 1))
        testFailure(grammar, inputs[i][0])
        testFailure(grammar, inputs[i][1])
        testSuccess(grammar, inputs[i][2], ["1"])
        testFailure(grammar, inputs[i][3])
        testFailure(grammar, inputs[i][4])
        testFailure(grammar, inputs[i][5])
        testFailure(grammar, inputs[i][6])

        grammar = makeGrammar(withOpenClose[i], withDelimiter[i], Range(0, 2))
        testFailure(grammar, inputs[i][0])
        testSuccess(grammar, inputs[i][1], [])
        testSuccess(grammar, inputs[i][2], ["1"])
        testSuccess(grammar, inputs[i][3], ["1", "2"])
        testFailure(grammar, inputs[i][4])
        testFailure(grammar, inputs[i][5])
        testFailure(grammar, inputs[i][6])

        grammar = makeGrammar(withOpenClose[i], withDelimiter[i], Range(1, 2))
        testFailure(grammar, inputs[i][0])
        testFailure(grammar, inputs[i][1])
        testSuccess(grammar, inputs[i][2], ["1"])
        testSuccess(grammar, inputs[i][3], ["1", "2"])
        testFailure(grammar, inputs[i][4])
        testFailure(grammar, inputs[i][5])
        testFailure(grammar, inputs[i][6])


if __name__ == "__main__":
    testKeepDelimiters()
    test()
