from __future__ import annotations
from typing import TYPE_CHECKING, List, cast

from nls.core.terminal import EPSILON
from nls.ebnf.repeat import Repeat
from nls.ebnf.rule import Rule
from nls.ebnf.star import Star
from nls.evaluator import ALL_CHILDREN_EVALUATOR
from nls.core.production import AstBuilder, ExtensionListener, DEFAULT_ASTBUILDER
from nls.core.nonterminal import NonTerminal
from nls.util.range import Range, PLUS, STAR, OPTIONAL
from nls.parsednode import ParsedNode

if TYPE_CHECKING:
    from nls.core.symbol import Symbol
    from nls.core.bnf import BNF
    from nls.core.defaultparsednode import DefaultParsedNode


class Join(Rule):
    def __init__(self,
                 tgt: NonTerminal,
                 entry: Symbol,
                 jopen: Symbol,
                 jclose: Symbol,
                 jdelimiter: Symbol,
                 cardinality: Range):
        super().__init__("join", tgt, [entry])
        self._jopen = jopen
        self._jclose = jclose
        self._jdelimiter = jdelimiter
        self._cardinality = cardinality
        self._onlyKeepEntries = True
        self.setEvaluator(ALL_CHILDREN_EVALUATOR)

    def getEntry(self) -> Symbol:
        return self.children[0]

    @property
    def cardinality(self) -> Range:
        return self._cardinality

    @cardinality.setter
    def cardinality(self, value: Range) -> None:
        self._cardinality = value

    @property
    def onlyKeepEntries(self) -> bool:
        return self._onlyKeepEntries

    @onlyKeepEntries.setter
    def onlyKeepEntries(self, value: bool) -> None:
        self._onlyKeepEntries = value

    def createBNF(self, grammar: BNF):
        first = self.getEntry()
        next = NonTerminal("next-" + NonTerminal.makeRandomSymbol())
        hasOpen = self._jopen is not None and not self._jopen.isEpsilon()
        hasClose = self._jclose is not None and not self._jclose.isEpsilon()
        hasDelimiter = self._jdelimiter is not None and not self._jdelimiter.isEpsilon()

        if hasDelimiter:
            p = self.addProduction(grammar, self, next, [self._jdelimiter, first])

            def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]) -> None:
                nthEntry = cast(ParsedNode, parent).nthEntryInParent + 1
                children[0].name = "delimiter"
                children[1].name = self.getNameForChild(nthEntry)
            p.onExtension = ExtensionListener(onExtension)

            if self._onlyKeepEntries:
                p.astBuilder = AstBuilder(lambda parent, children: parent.addChildren([children[1]]))
            else:
                p.astBuilder = DEFAULT_ASTBUILDER

        else:
            p = self.addProduction(grammar, self, next, [first])

            def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
                nthEntry = cast(ParsedNode, parent).nthEntryInParent + 1
                children[0].name = self.getNameForChild(nthEntry)
            p.onExtension = ExtensionListener(onExtension)
            p.astBuilder = AstBuilder(lambda parent, children: parent.addChildren([children[0]]))

        def buildAST(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
            parent.addChildren([children[0]])
            for pn in children[1].children:
                parent.addChildren(pn.children)
        astBuilder = AstBuilder(buildAST)

        def buildAST(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
            pass
        noOpAstBuilder = AstBuilder(buildAST)

        repetition = NonTerminal("repetition" + NonTerminal.makeRandomSymbol())

        # +: L -> first next*
        if self._cardinality == PLUS:
            star = Star(None, next)
            star.setParsedChildNames(["next"])
            star.createBNF(grammar)
            p = self.addProduction(grammar, self, repetition, [first, star.tgt])

            def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
                children[0].name = self.getNameForChild(0)
                children[1].name = "star"
            p.onExtension = ExtensionListener(onExtension)
            p.astBuilder = astBuilder

        # *: L -> first next*
        #    L -> epsilon
        elif self._cardinality == STAR:
            star = Star(None, next)
            star.setParsedChildNames(["next"])
            star.createBNF(grammar)

            p1 = self.addProduction(grammar, self, repetition, [first, star.tgt])
            p2 = self.addProduction(grammar, self, repetition, [EPSILON])

            p1.astBuilder = astBuilder
            p2.astBuilder = noOpAstBuilder

            def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
                children[0].name = self.getNameForChild(0)
                children[1].name = "star"
            p1.onExtension = ExtensionListener(onExtension)

        # ?: L -> first
        #    L -> epsilon
        elif self._cardinality == OPTIONAL:
            p1 = self.addProduction(grammar, self, repetition, [first])
            p2 = self.addProduction(grammar, self, repetition, [])

            def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
                children[0].name = self.getNameForChild(0)
            p1.onExtension = ExtensionListener(onExtension)
            p2.astBuilder = noOpAstBuilder

        # Dealing with a specific range
        else:
            lower = self._cardinality.lower
            upper = self._cardinality.upper

            if lower == 0 and upper == 0:
                p = self.addProduction(grammar, self, repetition, [])
                p.astBuilder = noOpAstBuilder

            elif lower == 1 and upper == 1:
                p = self.addProduction(grammar, self, repetition, [first])  # using default ASTBuilder

                def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
                    children[0].name = self.getNameForChild(0)
                p.onExtension = ExtensionListener(onExtension)

            else:
                if lower <= 0:
                    repeat = Repeat(None, next, 0, upper - 1)
                    repeat.setParsedChildNames(["next"])
                    repeat.createBNF(grammar)
                    p = self.addProduction(grammar, self, repetition, [first, repeat.tgt])
                    p.astBuilder = astBuilder

                    def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
                        children[0].name = self.getNameForChild(0)
                        children[1].name = "repeat"
                    p.onExtension = ExtensionListener(onExtension)

                    p = self.addProduction(grammar, self, repetition, [EPSILON])
                    p.astBuilder = noOpAstBuilder

                else:
                    repeat = Repeat(None, next, lower - 1, upper - 1)
                    repeat.setParsedChildNames(["next"])
                    repeat.createBNF(grammar)
                    p = self.addProduction(grammar, self, repetition, [first, repeat.tgt])
                    p.astBuilder = astBuilder

                    def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
                        children[0].name = self.getNameForChild(0)
                        children[1].name = "repeat"
                    p.onExtension = ExtensionListener(onExtension)

        if not hasOpen and not hasClose:
            p = self.addProduction(grammar, self, self.tgt, [repetition])

            def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
                children[0].name = "repetition"
            p.onExtension = ExtensionListener(onExtension)

            p.astBuilder = AstBuilder(lambda parent, children: parent.addChildren(children[0].children))

        else:
            p = self.addProduction(grammar, self, self.tgt, [self._jopen, repetition, self._jclose])

            def onExtension(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
                if not self.onlyKeepEntries:
                    children[0].name = "open"
                children[1].name = "repetition"
                if not self.onlyKeepEntries:
                    children[2].name = "close"
            p.onExtension = ExtensionListener(onExtension)

            def buildAST(parent: DefaultParsedNode, children: List[DefaultParsedNode]):
                if not self.onlyKeepEntries:
                    parent.addChildren([children[0]])
                parent.addChildren(children[1].children)
                if not self.onlyKeepEntries:
                    parent.addChildren([children[2]])
            p.astBuilder = AstBuilder(buildAST)
