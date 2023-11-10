from __future__ import annotations

from typing import TYPE_CHECKING, cast, List, Dict

from nls.core.autocompletion import Autocompletion
from nls.core.lexer import Lexer
from nls.core.parsingstate import ParsingState
from nls.core.rdparser import RDParser
from nls.core.terminal import literal, characterClass, Terminal
from nls.ebnf.ebnf import EBNF
from nls.ebnf import ebnfparsednodefactory
from nls.ebnf.ebnfparser import EBNFParser, ParseStartListener
from nls.evaluator import Evaluator, FIRST_CHILD_EVALUATOR, DEFAULT_EVALUATOR
from nls.util.range import OPTIONAL, PLUS, STAR, Range
from nls.core import graphviz
from nls.core.nonterminal import NonTerminal
from nls.autocompleter import Autocompleter, DEFAULT_INLINE_AUTOCOMPLETER, EntireSequenceAutocompleter
from nls.parsednode import ParsedNode
from nls.core.symbol import Symbol
from nls.core.named import Named

if TYPE_CHECKING:
    from nls.ebnf.rule import Rule, NamedRule
    from nls.ebnf.ebnfcore import EBNFCore


class Parser:

    def __init__(self):
        self._parseStartListeners: List[ParseStartListener] = []
        self._grammar = EBNF()
        self._targetGrammar = EBNF()
        self._compiled = False
        self.QUANTIFIER = self.quantifier()
        self.IDENTIFIER = self.identifier()
        self.VARIABLE_NAME = self.variableName()
        self.ENTRY_NAME = self.entryName()
        self.LIST = self.list()
        self.TUPLE = self.tuple()
        self.CHARACTER_CLASS = self.characterClass()
        self.TYPE = self.typ()
        self.VARIABLE = self.variable()
        self.NO_VARIABLE = self.noVariable()
        self.EXPRESSION = self.expression()

        self.LINEBREAK = literal("\n")
        self.LINEBREAK_STAR = self._targetGrammar.star("linebreak-star", self.LINEBREAK.withName())
        self.program()

        self._symbol2Autocompletion: Dict[str, str] = {}

    @property
    def grammar(self) -> EBNF:
        return self._grammar

    @property
    def targetGrammar(self) -> EBNF:
        return self._targetGrammar

    def defineSentence(
            self,
            pattern: str,
            evaluator: Evaluator or None = None,
            autocompleter: Autocompleter or bool or None = None) -> NamedRule:

        return self.defineType("sentence", pattern, evaluator, autocompleter)

    def defineType(
            self,
            typ: str,
            pattern: str,
            evaluator: Evaluator or None = None,
            autocompleter: Autocompleter or bool or None = None) -> NamedRule:
        autocompleterToUse = autocompleter
        if type(autocompleter) is bool and autocompleter:
            autocompleterToUse = EntireSequenceAutocompleter(self._targetGrammar, self._symbol2Autocompletion)
        elif type(autocompleter) is bool and not autocompleter:
            autocompleterToUse = DEFAULT_INLINE_AUTOCOMPLETER

        self._grammar.compile(self.EXPRESSION.tgt)
        parser = RDParser(self._grammar.getBNF(), Lexer(pattern), ebnfparsednodefactory.INSTANCE)
        pn = parser.parse()
        if pn.matcher.state != ParsingState.SUCCESSFUL:
            raise Exception("Parsing failed")
        rhs = cast(List[Named], pn.evaluate())

        newRule = self._targetGrammar.sequence(typ, rhs)
        if evaluator is not None:
            newRule.setEvaluator(evaluator)
        if autocompleterToUse is not None:
            newRule.setAutocompleter(autocompleterToUse)

        return newRule.withName(typ)

    def compile(self, symbol: Symbol = None) -> None:
        if symbol is None:
            symbol = self._targetGrammar.getSymbol("program")
        self._targetGrammar.compile(symbol)
        self._compiled = True

    def parse(self, text: str, autocompletions: List[Autocompletion] or None = None) -> ParsedNode:
        if not self._compiled:
            self.compile()
        self._symbol2Autocompletion.clear()
        rdParser = EBNFParser(self._targetGrammar.getBNF(), Lexer(text))
        rdParser.addParseStartListener(ParseStartListener(self.fireParsingStarted))
        return cast(ParsedNode, rdParser.parse(autocompletions))

    def quantifier(self) -> Rule:
        g = self._grammar
        return g.orrule(
            "quantifier",
            [
                g.sequence(None, [literal("?").withName()])          .setEvaluator(Evaluator(lambda pn: OPTIONAL)).withName("optional"),
                g.sequence(None, [literal("+").withName()])          .setEvaluator(Evaluator(lambda pn: PLUS))    .withName("plus"),
                g.sequence(None, [literal("*").withName()])          .setEvaluator(Evaluator(lambda pn: STAR))    .withName("star"),
                g.sequence(None, [g.INTEGER_RANGE.withName("range")]).setEvaluator(FIRST_CHILD_EVALUATOR)         .withName("range"),
                g.sequence(None, [g.INTEGER.withName("int")])
                 .setEvaluator(Evaluator(lambda pn: Range(int(pn.evaluate(0)))))
                 .withName("fixed")
            ])

    def identifier(self, name: str = None) -> Rule:
        if name is None:
            name = "identifier"
        g = self._grammar
        return g.sequence(
            name, [
                characterClass("[A-Za-z_]").withName(),
                g.optional(
                    None,
                    g.sequence(
                        None, [
                            g.star(None, characterClass("[A-Za-z0-9_-]").withName()).withName("star"),
                            characterClass("[A-Za-z0-9_]").withName()
                        ]
                    ).withName("seq")
                ).withName("opt")
            ])

    def variableName(self) -> Rule:
        return self._grammar.plus(
            "var-name",
            characterClass("[^:{}]").withName()
        ).setEvaluator(DEFAULT_EVALUATOR)

    def entryName(self) -> Rule:
        return self.identifier("entry-name")

    def list(self) -> Rule:
        g = self._grammar
        ret = g.sequence(
            "list", [
                literal("list").withName(),
                g.WHITESPACE_STAR.withName("ws*"),
                literal("<").withName(),
                g.WHITESPACE_STAR.withName("ws*"),
                self.IDENTIFIER.withName("type"),
                g.WHITESPACE_STAR.withName("ws*"),
                literal(">").withName()
            ])

        def evaluate(pn: ParsedNode) -> object:
            identifier: str = cast(str, pn.evaluateChildByNames("type"))
            entry: Symbol or None = self._targetGrammar.getSymbol(identifier)

            namedEntry = \
                cast(Terminal, entry).withName(identifier) if isinstance(entry, Terminal) else \
                cast(NonTerminal, entry).withName(identifier)

            return self._targetGrammar.list(None, namedEntry).tgt

        ret.setEvaluator(Evaluator(evaluate))
        return ret

    def tuple(self) -> Rule:
        g = self._grammar
        ret = g.sequence(
            "tuple",
            [
                literal("tuple").withName(),
                g.WHITESPACE_STAR.withName("ws*"),
                literal("<").withName(),
                g.WHITESPACE_STAR.withName("ws*"),
                self.IDENTIFIER.withName("type"),
                g.plus(
                    None,
                    g.sequence(
                        None,
                        [
                            g.WHITESPACE_STAR.withName("ws*"),
                            literal(",").withName(),
                            g.WHITESPACE_STAR.withName("ws*"),
                            self.ENTRY_NAME.withName("entry-name"),
                            g.WHITESPACE_STAR.withName("ws*")
                        ]
                    ).withName("sequence-names")
                ).withName("plus-names"),
                literal(">").withName()
            ])

        def evaluate(pn: ParsedNode) -> object:
            typ = str(pn.evaluateChildByNames("type"))
            plus = pn.getChild("plus-names")
            entryNames = list(map(lambda dpn: str(dpn.evaluate("entry-name")), plus.children))

            entry = self._targetGrammar.getSymbol(typ)
            namedEntry = \
                cast(Terminal, entry).withName() if isinstance(entry, Terminal) else \
                cast(NonTerminal, entry).withName()
            return self._targetGrammar.tuple(None, namedEntry, entryNames).tgt

        ret.setEvaluator(Evaluator(evaluate))
        return ret

    def characterClass(self) -> Rule:
        g = self._grammar
        ret = g.sequence(
            "character-class",
            [
                literal("[").withName(),
                g.plus(None, characterClass("[^]]").withName()).withName("plus"),
                literal("]").withName()
            ]
        ).setEvaluator(Evaluator(lambda pn: characterClass(pn.getParsedString())))
        return ret

    def typ(self) -> Rule:
        g = self._grammar
        typ = g.sequence(None, [self.IDENTIFIER.withName("identifier")])

        def evaluate(pn: ParsedNode):
            string: str = pn.getParsedString()
            symbol: Symbol = self._targetGrammar.getSymbol(string)
            if symbol is None:
                raise Exception("Unknow type '" + string + "'")
            return symbol

        typ.setEvaluator(Evaluator(evaluate))
        return g.orrule(
            "type",
            [
                typ.withName("type"),
                self.LIST.withName("list"),
                self.TUPLE.withName("tuple"),
                self.CHARACTER_CLASS.withName("character-class")
            ]
        )

    def variable(self) -> Rule:
        g = self._grammar
        ret = g.sequence(
            "variable",
            [
                literal("{").withName(),
                self.VARIABLE_NAME.withName("variable-name"),
                g.optional(
                    None,
                    g.sequence(
                        None,
                        [
                            literal(":").withName(),
                            self.TYPE.withName("type")
                        ]
                    ).withName("seq-type")
                ).withName("opt-type"),
                g.optional(
                    None,
                    g.sequence(
                        None,
                        [
                            literal(":").withName(),
                            self.QUANTIFIER.withName("quantifier")
                        ]
                    ).withName("seq-quantifier")
                ).withName("opt-quantifier"),
                literal("}").withName()
            ]
        )

        def evaluate(pn: ParsedNode) -> object:
            variableName = str(pn.evaluate("variable-name"))
            typeObject = pn.evaluate("opt-type", "seq-type", "type")
            symbol = literal(variableName) if typeObject is None else cast(Symbol, typeObject)
            namedSymbol = \
                cast(Terminal, symbol).withName(variableName) if symbol.isTerminal() else \
                cast(NonTerminal, symbol).withName(variableName)

            quantifierObject = pn.evaluate("opt-quantifier", "seq-quantifier", "quantifier")
            if quantifierObject is not None:
                range = cast(Range, quantifierObject)
                if range == STAR:
                    symbol = self._targetGrammar.star(None, namedSymbol).tgt
                elif range == PLUS:
                    symbol = self._targetGrammar.plus(None, namedSymbol).tgt
                elif range == OPTIONAL:
                    symbol = self._targetGrammar.optional(None, namedSymbol).tgt
                else:
                    symbol = self._targetGrammar.repeat(None, namedSymbol, rfrom=range.lower, rto=range.upper).tgt
                namedSymbol = cast(NonTerminal, symbol).withName(variableName)

            return namedSymbol

        ret.setEvaluator(Evaluator(evaluate))
        return ret

    def noVariable(self) -> Rule:
        g = self._grammar
        ret = g.sequence(
            "no-variable",
            [
                characterClass("[^ \t\n{]").withName(),
                g.optional(
                    None,
                    g.sequence(
                        None,
                        [
                            g.star(
                                None,
                                characterClass("[^{\n]").withName()
                            ).withName("middle"),
                            characterClass("[^ \t\n{]").withName()
                        ]
                    ).withName("seq")
                ).withName("tail")
            ])
        ret.setEvaluator(Evaluator(lambda pn: literal(pn.getParsedString()).withName(pn.getParsedString())))
        return ret

    def expression(self) -> Rule:
        g = self._grammar
        ret = g.joinWithRange(
            "expression",
            g.orrule(None,
                     [
                        self.NO_VARIABLE.withName("no-variable"),
                        self.VARIABLE.withName("variable")
                     ]).withName("or"),
            jopen=None,
            jclose=None,
            delimiter=g.WHITESPACE_STAR.tgt,
            onlyKeepEntries=False,
            cardinality=PLUS)

        def evaluate(pn: ParsedNode) -> object:
            nChildren = pn.numChildren()
            rhsList = [pn.evaluateChildByIndex(0)]
            for i in range(1, nChildren):
                child: ParsedNode = pn.getChildByIndex(i)
                if i % 2 == 0:
                    rhsList.append(cast(Named, child.evaluateSelf()))
                else:
                    hasWS = child.numChildren() > 0
                    if hasWS:
                        rhsList.append(self._targetGrammar.WHITESPACE_PLUS.withName("ws+"))
            return rhsList

        ret.setEvaluator(Evaluator(evaluate))
        return ret

    def program(self) -> Rule:
        return self._targetGrammar.join(
            "program",
            NonTerminal("sentence").withName("sentence"),
            jopen=self.LINEBREAK_STAR.tgt,
            jclose=self.LINEBREAK_STAR.tgt,
            delimiter=self.LINEBREAK_STAR.tgt,
            cardinality=STAR
        )

    def addParseStartListener(self, listener: ParseStartListener) -> None:
        self._parseStartListeners.append(listener)

    def removeParseStartListener(self, listener: ParseStartListener) -> None:
        self._parseStartListeners.remove(listener)

    def fireParsingStarted(self):
        for listener in self._parseStartListeners:
            listener.parsingStarted()
