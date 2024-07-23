from __future__ import annotations

from typing import TYPE_CHECKING, cast, List, Dict, Callable

from nlScript.core.autocompletion import Autocompletion
from nlScript.core.lexer import Lexer
from nlScript.core.parsingstate import ParsingState
from nlScript.core.rdparser import RDParser
from nlScript.core.terminal import literal, characterClass, Terminal
from nlScript.ebnf.ebnf import EBNF
from nlScript.ebnf import ebnfparsednodefactory
from nlScript.ebnf.ebnfparser import EBNFParser, ParseStartListener
from nlScript.evaluator import Evaluator, FIRST_CHILD_EVALUATOR, DEFAULT_EVALUATOR
from nlScript.util.range import OPTIONAL, PLUS, STAR, Range
from nlScript.core.nonterminal import NonTerminal
from nlScript.autocompleter import Autocompleter, DEFAULT_INLINE_AUTOCOMPLETER, EntireSequenceAutocompleter
from nlScript.parsednode import ParsedNode
from nlScript.core.symbol import Symbol
from nlScript.core.named import Named
from nlScript.ebnf.join import Join

if TYPE_CHECKING:
    from nlScript.ebnf.rule import Rule, NamedRule


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

        self._symbol2Autocompletion: Dict[str, List[Autocompletion]] = {}

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
            autocompleter: Autocompleter or Callable[[ParsedNode, bool], List[Autocompletion] or None] or bool or None = None) -> NamedRule:

        return self.defineType("sentence", pattern, evaluator, autocompleter)

    def defineType(
            self,
            typ: str,
            pattern: str,
            evaluator: Evaluator or Callable[[ParsedNode], object] or None = None,
            autocompleter: Autocompleter or Callable[[ParsedNode, bool], List[Autocompletion] or None] or bool or None = None) -> NamedRule:
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

    def undefineType(self, atype: str) -> None:
        unitsSymbol: NonTerminal = cast(NonTerminal, self.targetGrammar.getSymbol(atype))
        self.targetGrammar.removeRules(unitsSymbol)
        self._compiled = False

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
                g.sequence(None, [literal("?").withName()])          .setEvaluator(lambda pn: OPTIONAL)  .withName("optional"),
                g.sequence(None, [literal("+").withName()])          .setEvaluator(lambda pn: PLUS)      .withName("plus"),
                g.sequence(None, [literal("*").withName()])          .setEvaluator(lambda pn: STAR)      .withName("star"),
                g.sequence(None, [g.INTEGER_RANGE.withName("range")]).setEvaluator(FIRST_CHILD_EVALUATOR).withName("range"),
                g.sequence(None, [g.INTEGER.withName("int")])
                 .setEvaluator(lambda pn: Range(int(pn.evaluate(0))))
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

    # evaluates to the target grammar's list rule (i.e. Join).
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

            return self._targetGrammar.list(None, namedEntry)

        ret.setEvaluator(evaluate)
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

        ret.setEvaluator(evaluate)
        return ret

    def characterClass(self) -> Rule:
        g = self._grammar
        ret = g.sequence(
            "character-class",
            [
                literal("[").withName(),
                g.plus(None,
                    g.orrule(None,
                    [
                        characterClass("[^]]").withName(),
                        literal("\\]").withName()
                    ]).withName()
                ).withName("plus"),
                literal("]").withName()
            ]
        ).setEvaluator(lambda pn: characterClass(pn.getParsedString()))
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

        typ.setEvaluator(evaluate)
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
            quantifierObject = pn.evaluate("opt-quantifier", "seq-quantifier", "quantifier")

            # typeObject is either
            # - a type (symbol) from the target grammar, or
            # - a character-class (i.e. a terminal), or
            # - a tuple (i.e. symbol of the tuple in the target grammar), or
            # - a list (i.e. a Rule, or more specifically a Join).
            if isinstance(typeObject, Join):
                join = cast(Join, typeObject)
                if quantifierObject is not None:
                    join.cardinality = cast(Range, quantifierObject)
                return join.tgt.withName(variableName)

            symbol = literal(variableName) if typeObject is None else cast(Symbol, typeObject)
            namedSymbol = \
                cast(Terminal, symbol).withName(variableName) if symbol.isTerminal() else \
                cast(NonTerminal, symbol).withName(variableName)

            if quantifierObject is not None:
                autocompleter: Autocompleter | None = None
                # set a new fallback autocompleter. This is important for e.g. {bla:[a-z]:4} or {bla:digit:4}
                if isinstance(typeObject, Terminal):
                    autocompleter = DEFAULT_INLINE_AUTOCOMPLETER
                range = cast(Range, quantifierObject)
                if range == STAR:
                    symbol = self._targetGrammar.star(None, namedSymbol).setAutocompleter(autocompleter).tgt
                elif range == PLUS:
                    symbol = self._targetGrammar.plus(None, namedSymbol).setAutocompleter(autocompleter).tgt
                elif range == OPTIONAL:
                    symbol = self._targetGrammar.optional(None, namedSymbol).setAutocompleter(autocompleter).tgt
                else:
                    symbol = self._targetGrammar.repeat(None, namedSymbol, rfrom=range.lower, rto=range.upper)\
                        .setAutocompleter(autocompleter).tgt
                namedSymbol = cast(NonTerminal, symbol).withName(variableName)

            return namedSymbol

        ret.setEvaluator(evaluate)
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
        ret.setEvaluator(lambda pn: literal(pn.getParsedString()).withName(pn.getParsedString()))
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

        ret.setEvaluator(evaluate)
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
