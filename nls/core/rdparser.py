from __future__ import annotations

from typing import TYPE_CHECKING, List, cast, Set

from nls.core.graphviz import toVizDotLink
from nls.core.parsingstate import ParsingState
from nls.core.matcher import Matcher
from nls.autocompleter import IAutocompleter
from nls.core.bnf import BNF
from nls.core.nonterminal import NonTerminal
from nls.core.terminal import Terminal
from nls.core.autocompletion import Autocompletion

import sys

from nls.parseexception import ParseException

sys.setrecursionlimit(500)

if TYPE_CHECKING:
    from nls.core.lexer import Lexer
    from nls.core.parsednodefactory import ParsedNodeFactory
    from nls.core.defaultparsednode import DefaultParsedNode
    from nls.core.symbol import Symbol
    from nls.core.production import Production


class RDParser:

    def __init__(self, grammar: BNF, lexer: Lexer, parsedNodeFactory: ParsedNodeFactory):
        self._grammar = grammar
        self._lexer = lexer
        self._parsedNodeFactory = parsedNodeFactory

    def getLexer(self) -> Lexer:
        return self._lexer

    def getGrammar(self) -> BNF:
        return self._grammar

    def getParsedNodeFactory(self) -> ParsedNodeFactory:
        return self._parsedNodeFactory

    def parse(self, autocompletions: List[Autocompletion] = None) -> DefaultParsedNode:
        seq = SymbolSequence(BNF.ARTIFICIAL_START_SYMBOL)
        endOfInput: List[SymbolSequence] = []
        parsedSequence = self.parseRecursive(seq, endOfInput)
        if autocompletions is not None:
            self.collectAutocompletions(endOfInput, autocompletions)
        if autocompletions is not None and len(autocompletions) > 0 and autocompletions[-1] is None:
            del(autocompletions[-1])
        last: List[DefaultParsedNode or None] = [None]
        ret = self.createParsedTree(parsedSequence, last)
        ret = self.buildAst(ret)
        if ret.matcher.state == ParsingState.FAILED:
            print(toVizDotLink(ret))
            raise ParseException(ret, last[0], self)
        return ret

    def buildAst(self, pn: DefaultParsedNode) -> DefaultParsedNode:
        children = []
        for i in range(pn.numChildren()):
            children.append(self.buildAst(pn.getChild(i)))

        pn.removeAllChildren()
        if pn.production is not None:
            pn.production.buildAST(pn, children)

        return pn

    def collectAutocompletions(self, endOfInput: List[SymbolSequence], autocompletions: List[Autocompletion]) -> None:
        autocompletingParents: List[DefaultParsedNode] = []
        for seq in endOfInput:
            self.collectAutocompletingParents(seq, autocompletingParents)
        done: Set[str] = set()
        for autocompletingParent in autocompletingParents:
            prod = autocompletingParent.production
            if prod is not None:
                key = prod.left.symbol + ":"
                for s in prod.right:
                    key = key + s.symbol
            else:
                key = autocompletingParent.symbol.symbol
            if key not in done:
                self.addAutocompletions(autocompletingParent, autocompletions)
                done.add(key)

    def collectAutocompletingParents(self, symbolSequence: SymbolSequence, autocompletingParents: List[DefaultParsedNode]):
        last: List[DefaultParsedNode or None] = [None]
        self.createParsedTree(symbolSequence, last)

        # get a trace to the root
        pathToRoot: List[DefaultParsedNode] = []
        parent: DefaultParsedNode = last[0]
        while parent is not None:
            pathToRoot.append(parent)
            parent = parent.parent

        # find the node closest to the root which provides autocompletion
        autocompletingParent: DefaultParsedNode or None = None
        pathToRoot.reverse()
        for tmp in pathToRoot:
            if tmp.doesAutocomplete():
                autocompletingParent = tmp
                break
        if autocompletingParent is not None:
            autocompletingParents.append(autocompletingParent)

    def addAutocompletions(self, autocompletingParent: DefaultParsedNode, autocompletions: List[Autocompletion or None]):
        if len(autocompletions) > 0 and autocompletions[-1] is None:
            return
        autocompletingParentStart = autocompletingParent.matcher.pos
        alreadyEntered = self._lexer.substring(autocompletingParentStart)
        completion = autocompletingParent.getAutocompletion(False)
        if completion is not None and len(completion) > 0:
            for c in completion.split(";;;"):
                if c == IAutocompleter.VETO:
                    # autocompletions.clear()
                    autocompletions.append(None)  # to prevent further autocompletion
                    return
                ac = Autocompletion(c, alreadyEntered)
                if ac not in autocompletions:
                    autocompletions.append(ac)

    def parseRecursive(self, symbolSequence: SymbolSequence, endOfInput: List[SymbolSequence]) -> SymbolSequence:
        # print("parseRecursive:")
        # print("  symbol sequence = " + str(symbolSequence))
        # print("  lexer           = " + str(self._lexer))
        nextS = symbolSequence.getCurrentSymbol()
        # print("next = " + str(nextS))
        while nextS.isTerminal():
            # print("next is a terminal node, lexer pos = " + str(self._lexer.pos))
            # if nextS.symbol == "385nm":
            #     print("debug")
            matcher = cast(Terminal, nextS).matches(self._lexer)
            # print("matcher = " + str(matcher))
            symbolSequence.addMatcher(matcher)
            if matcher.state == ParsingState.END_OF_INPUT and endOfInput is not None:
                endOfInput.append(symbolSequence)

            if matcher.state != ParsingState.SUCCESSFUL:
                return symbolSequence

            symbolSequence.incrementPosition()
            self._lexer.fwd(len(matcher.parsed))
            if self._lexer.isDone():
                return symbolSequence
            nextS = symbolSequence.getCurrentSymbol()

        u = cast(NonTerminal, nextS)
        alternatives = self._grammar.getProductions(u)
        best = None
        lexerPosOfBest = self._lexer.pos
        for alternate in alternatives:
            lexerPos = self._lexer.pos
            nextSequence = symbolSequence.replaceCurrentSymbol(alternate)
            parsedSequence = self.parseRecursive(nextSequence, endOfInput)
            m = parsedSequence.getLastMatcher()
            if m is not None:
                if m.state == ParsingState.SUCCESSFUL:
                    return parsedSequence
                if best is None or m.isBetterThan(best.getLastMatcher()):
                    best = parsedSequence
                    lexerPosOfBest = self._lexer.pos
            # print("reset lexer pos to " + str(lexerPos))
            self._lexer.pos = lexerPos

        if best is not None:
            self._lexer.pos = lexerPosOfBest

        return best

    def createParsedTree(self,
                         leafSequence: SymbolSequence,
                         retLast: List[DefaultParsedNode] or List[None]) -> DefaultParsedNode:
        parsedNodeSequence = []
        nParsedMatchers = len(leafSequence.parsedMatchers)
        for i, symbol in enumerate(leafSequence.sequence):
            # TODO maybe this should not be 0:
            matcher = leafSequence.parsedMatchers[i] if i < nParsedMatchers else Matcher(ParsingState.NOT_PARSED, 0, "")
            pn = self._parsedNodeFactory.createNode(matcher, symbol, None)
            parsedNodeSequence.append(pn)

        if retLast is not None:
            retLast[0] = parsedNodeSequence[nParsedMatchers - 1]

        childSequence = leafSequence
        while childSequence.parent is not None:
            parentSequence = childSequence.parent
            productionToCreateChildSequence = childSequence.production
            pos = parentSequence.pos
            rhs = productionToCreateChildSequence.right
            lhs = productionToCreateChildSequence.left
            rhsSize = len(rhs)
            childList = parsedNodeSequence[pos:pos + rhsSize]

            matcher = matcherFromChildSequence(childList)
            newParent = self._parsedNodeFactory.createNode(matcher, lhs, productionToCreateChildSequence)
            newParent.addChildren(childList)
            del(parsedNodeSequence[pos:pos + rhsSize])
            parsedNodeSequence.insert(pos, newParent)

            childSequence = childSequence.parent

        root = parsedNodeSequence[0]
        notifyExtensionListeners(root)
        return root


def notifyExtensionListeners(pn: DefaultParsedNode) -> None:
    production = pn.production
    if production is not None:
        production.wasExtended(pn, pn.children)
        for child in pn.children:
            notifyExtensionListeners(child)


def matcherFromChildSequence(children: List[DefaultParsedNode]) -> Matcher:
    pos = -1
    state = ParsingState.NOT_PARSED
    parsed = ""
    for child in children:
        # already encountered EOI or FAILED before, do nothing
        if state == ParsingState.END_OF_INPUT or state == ParsingState.FAILED:
            break
        matcher = child.matcher
        childState = matcher.state
        if childState != ParsingState.NOT_PARSED:
            if pos is -1:
                pos = matcher.pos  # parent pos is the pos of the first child which is not NOT_PARSED
            if state == ParsingState.NOT_PARSED or not childState.isBetterThan(state):
                state = childState
        parsed += matcher.parsed

    if pos is -1:
        pos = 0
    return Matcher(state, pos, parsed)


class SymbolSequence:

    def __init__(self, start: Symbol or None):
        self._sequence = [start] if start is not None else []
        self._pos = 0
        self._parent = None
        self._production = None
        self._parsedMatchers = []

    def getLastMatcher(self) -> Matcher:
        return self._parsedMatchers[-1]

    def addMatcher(self, matcher: Matcher) -> None:
        self._parsedMatchers.append(matcher)

    def getCurrentSymbol(self) -> Symbol:
        return self._sequence[self._pos]

    def replaceCurrentSymbol(self, production: Production) -> SymbolSequence:
        copy = SymbolSequence(None)
        copy._sequence = self._sequence.copy()
        copy._pos = self._pos
        copy._parent = self
        copy._production = production
        copy._parsedMatchers = self._parsedMatchers.copy()
        copy._sequence.pop(self._pos)
        replacements = production.right.copy()
        for idx, replacement in enumerate(replacements):
            copy._sequence.insert(self._pos + idx, replacement)
        return copy

    def incrementPosition(self) -> None:
        self._pos += 1

    def __str__(self) -> str:
        sb = ""
        for idx, sym in enumerate(self._sequence):
            if idx == self._pos:
                sb += "."
            sb += str(sym) + " -- "
        return sb

    @property
    def parsedMatchers(self):
        return self._parsedMatchers

    @property
    def sequence(self):
        return self._sequence

    @property
    def parent(self):
        return self._parent

    @property
    def production(self):
        return self._production

    @property
    def pos(self):
        return self._pos
