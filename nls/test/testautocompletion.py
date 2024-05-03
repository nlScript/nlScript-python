from typing import List, cast

from nls.autocompleter import Autocompleter
from nls.core import graphviz
from nls.core.autocompletion import Autocompletion, Purpose
from nls.core.bnf import BNF
from nls.core.lexer import Lexer
from nls.core.nonterminal import NonTerminal
from nls.core.parsingstate import ParsingState
from nls.core.rdparser import RDParser
from nls.core.terminal import literal, WHITESPACE, characterClass
from nls.ebnf import ebnfparsednodefactory
from nls.ebnf.ebnfcore import EBNFCore
from nls.ebnf.ebnfparser import ParseStartListener
from nls.ebnf.parselistener import ParseListener
from nls.evaluator import Evaluator
from nls.parsednode import ParsedNode
from nls.parser import Parser


def assertEquals(exp, real):
    if exp != real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def assertNotEquals(exp, real):
    if exp == real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def test01():
    test("", ["one ()"])
    test("o", ["one (o)"])
    test("one", ["${or} ()", "five ()"])
    test("onet", [])


def test02():
    parser = Parser()
    parser.defineSentence("The first digit of the number is {first:digit}.")
    autocompletions: List[Autocompletion] = []
    parser.parse("The first digit of the number is ", autocompletions)
    assertEquals(1, len(autocompletions))
    assertEquals("${first}", autocompletions[0].getCompletion(Purpose.FOR_INSERTION))


def test03():
    parser = Parser()
    parser.defineSentence("Define the output path {p:path}.")
    autocompletions: List[Autocompletion] = []
    parser.parse("", autocompletions)
    assertEquals(2, len(autocompletions))
    assertEquals("Define the output path", autocompletions[1].getCompletion(Purpose.FOR_INSERTION))


def test04():
    sentencesParsed: List[str] = []

    parser = Parser()
    parser.addParseStartListener(ParseStartListener(lambda: sentencesParsed.clear()))
    parser.defineSentence("{d:digit:+}.").onSuccessfulParsed(
        ParseListener(lambda pn: sentencesParsed.append(pn.getParsedString())))

    autocompletions: List[Autocompletion] = []

    parser.parse("1.22.333.", autocompletions)

    expected = ["1.", "22.", "333."]
    assertEquals(expected, sentencesParsed)


def test05():
    definedChannels: List[str] = []

    parser = Parser()
    parser.addParseStartListener(ParseStartListener(lambda: definedChannels.clear()))

    # parser.defineType("channel-name", "'{<name>:[A-Za-z0-9]:+}'",
    #                   None,
    #                   IfNothingYetEnteredAutocompleter("'${name}'"))

    parser.defineSentence("Define channel {channel-name:[A-Za-z0-9]:+}.", None)\
        .onSuccessfulParsed(ParseListener(lambda pn: definedChannels.append(pn.getParsedString("channel-name"))))

    parser.defineType("defined-channels", "'{channel:[A-Za-z0-9]:+}'",
            None,
            Autocompleter(lambda pn, justCheck: Autocompletion.literal(pn, definedChannels)))

    parser.defineSentence("Use channel {channel:defined-channels}.", None)

    autocompletions: List[Autocompletion] = []
    root = parser.parse(
            "Define channel DAPI.\n" +
            "Define channel A488.\n" +
            "Use channel 'DAPI'.\n" +
            "Use channel 'A488'.\n" +
            "Use channel ", autocompletions)
    print(graphviz.toVizDotLink(root))
    assertEquals(ParsingState.END_OF_INPUT, root.matcher.state)

    expected: List[str] = ["DAPI", "A488"]

    assertEquals(expected, [a.getCompletion(Purpose.FOR_INSERTION) for a in autocompletions])


def test06():
    ebnf = EBNFCore()

    sentence = ebnf.sequence("sentence", [
            literal("Define channel").withName(),
            WHITESPACE.withName("ws"),
            ebnf.plus("name",
                      characterClass("[A-Za-z]").withName()
            ).withName("name"),
            literal(".").withName()])
    program = ebnf.star("program",
            # n("sentence", sentence))
            NonTerminal("sentence").withName("sentence"))

    ebnf.compile(program.tgt)

    text = "Define channel DA.D"

    autocompletions: List[Autocompletion] = []

    bnf = ebnf.getBNF()
    print(bnf)
    parser = RDParser(bnf, Lexer(text), ebnfparsednodefactory.INSTANCE)
    pn = cast(ParsedNode, parser.parse(autocompletions))
    print(graphviz.toVizDotLink(pn))
    print(pn.matcher.state)
    assertEquals(ParsingState.END_OF_INPUT, pn.matcher.state)
    assertEquals(1, len(autocompletions))
    assertEquals("Define channel", autocompletions[0].getCompletion(Purpose.FOR_INSERTION))


def test07():
    parser = Parser()

    parser.defineType("led", "385nm", evaluator=None, autocompleter=Autocompleter(lambda e, justCheck: Autocompletion.literal(e, ["385nm"])))
    parser.defineType("led", "470nm", evaluator=None, autocompleter=Autocompleter(lambda e, justCheck: Autocompletion.literal(e, ["470nm"])))
    parser.defineType("led", "567nm", evaluator=None, autocompleter=Autocompleter(lambda e, justCheck: Autocompletion.literal(e, ["567nm"])))
    parser.defineType("led", "625nm", evaluator=None, autocompleter=Autocompleter(lambda e, justCheck: Autocompletion.literal(e, ["625nm"])))

    parser.defineType("led-power", "{<led-power>:int}%", evaluator=None, autocompleter=True)
    parser.defineType("led-setting", "{led-power:led-power} at {wavelength:led}", None, True)

    parser.defineSentence(
            "Excite with {led-setting:led-setting}.",
            None)

    autocompletions: List[Autocompletion] = []
    root = parser.parse("Excite with 10% at 3", autocompletions)
    assertEquals(ParsingState.END_OF_INPUT, root.matcher.state)
    assertEquals(1, len(autocompletions))
    assertEquals("385nm", autocompletions[0].getCompletion(Purpose.FOR_INSERTION))

    autocompletions.clear()
    root = parser.parse("Excite with 10% at ", autocompletions)
    print("autocompletions: " + str([a.getCompletion(Purpose.FOR_INSERTION) for a in autocompletions]))


def test08():
    parser = Parser()
    parser.defineType("my-color", "blue", None)
    parser.defineType("my-color", "green", None)
    parser.defineType("my-color", "({r:int}, {g:int}, {b:int})", None, True)
    parser.defineSentence("My favorite color is {color:my-color}.", None)

    autocompletions: List[Autocompletion] = []
    root = parser.parse("My favorite color is ", autocompletions)
    assertEquals(ParsingState.END_OF_INPUT, root.matcher.state)
    assertEquals(3, len(autocompletions))
    assertEquals("blue", autocompletions[0].getCompletion(Purpose.FOR_INSERTION))
    assertEquals("green", autocompletions[1].getCompletion(Purpose.FOR_INSERTION))
    assertEquals("(${r}, ${g}, ${b})", autocompletions[2].getCompletion(Purpose.FOR_INSERTION))


def test09():
    parser = Parser()
    parser.defineType("channel-name", "'{<name>:[A-Za-z0-9]:+}'",
                      Evaluator(lambda e: e.getParsedString("<name>")),
                      True)

    parser.defineSentence(
        "Define channel {channel-name:channel-name}.",
        None)

    autocompletions: List[Autocompletion] = []
    root: ParsedNode = parser.parse("Define channel 'D", autocompletions)

    print("autocompletions = " + str([ac.getCompletion(Purpose.FOR_INSERTION) for ac in autocompletions]))


def test(inp: str, expectedCompletion: List[str]) -> None:
    print("Testing " + inp)
    grammar = makeGrammar()
    lexer = Lexer(inp)
    parser = RDParser(grammar, lexer, ebnfparsednodefactory.INSTANCE)
    autocompletions: List[Autocompletion] = []
    pn = parser.parse(autocompletions)
    print(graphviz.toVizDotLink(pn))

    print("input: " + inp)
    print("completions: " + str(autocompletions))

    assertEquals(ParsingState.END_OF_INPUT, pn.matcher.state)
    assertEquals(expectedCompletion, getCompletionStrings(autocompletions))


def getCompletionStrings(autocompletions: List[Autocompletion]) -> List[str]:
    return list(map(lambda ac: ac.getCompletion(Purpose.FOR_INSERTION) + " (" + ac.getAlreadyEnteredText() + ")", autocompletions))


def makeGrammar() -> BNF:
    def getAutocompletion(pn: ParsedNode, justCheck: bool) -> List[Autocompletion] or None:
        if len(pn.getParsedString()) > 0:
            return Autocompletion.veto(pn)
        return Autocompletion.parameterized(pn, pn.name)
    grammar = EBNFCore()
    e = grammar.sequence("expr", [
            literal("one").withName(),
            grammar.star(None,
                grammar.orrule(None, [
                    literal("two").withName("two"),
                    literal("three").withName("three"),
                    literal("four").withName("four")]
                ).setAutocompleter(Autocompleter(getAutocompletion))
                .withName("or")
            ).withName("star"),
            literal("five").withName("five")]
    )

    grammar.compile(e.tgt)
    return grammar.getBNF()


if __name__ == "__main__":
    test08()
    test07()
    test06()
    test05()
    test04()
    test03()
    test02()
    test01()
