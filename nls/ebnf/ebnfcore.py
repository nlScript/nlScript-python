from __future__ import annotations

from nls.autocompleter import Autocompleter, DEFAULT_INLINE_AUTOCOMPLETER
from nls.core.autocompletion import Autocompletion, EntireSequence
from nls.core.terminal import WHITESPACE, literal, characterClass
from nls.ebnf.join import Join
from nls.ebnf.optional import Optional
from nls.ebnf.orrule import Or
from typing import TYPE_CHECKING, List, cast, Dict

from nls.core.bnf import BNF
from nls.ebnf.plus import Plus
from nls.ebnf.repeat import Repeat
from nls.ebnf.sequence import Sequence
from nls.ebnf.star import Star
from nls.evaluator import FIRST_CHILD_EVALUATOR, Evaluator
from nls.core.nonterminal import NonTerminal
from nls.util.range import Range, STAR

if TYPE_CHECKING:
    from nls.core.symbol import Symbol
    from nls.ebnf.rule import Rule
    from nls.core.named import Named
    from nls.parsednode import ParsedNode


class EBNFCore:
    def __init__(self, other: EBNFCore = None):
        self._symbols: {str, Symbol} = {} if other is None else other.symbols.copy()
        self._rules   = [] if other is None else other.rules.copy()
        self._bnf = BNF()
        self._compiled = False if other is None else other._compiled

    def copy(self):
        return EBNFCore(other=self)

    def getSymbol(self, typ: str) -> Symbol or None:
        if typ in self._symbols:
            return self._symbols[typ]
        return None

    def compile(self, topLevelSymbol: Symbol) -> None:
        self._compiled = False  # otherwise removeRules() and addRule() will complain
        # update the start symbol
        self.removeRules(BNF.ARTIFICIAL_START_SYMBOL)
        sequence = Sequence(BNF.ARTIFICIAL_START_SYMBOL, [topLevelSymbol, BNF.ARTIFICIAL_STOP_SYMBOL])
        self.addRule(sequence)
        sequence.setEvaluator(FIRST_CHILD_EVALUATOR)

        self._bnf.reset()
        for r in self.rules:
            r.createBNF(self._bnf)
        self._compiled = True

    def getBNF(self):
        return self._bnf

    @property
    def symbols(self) -> Dict[str, Symbol]:
        return self._symbols

    @property
    def rules(self) -> List[Rule]:
        return self._rules

    def getRules(self, target: NonTerminal) -> List[Rule]:
        return [r for r in self._rules if r.tgt == target]

    def plus(self, typ: str or None, child: Named) -> Rule:
        tgt = self.newOrExistingNonTerminal(typ)
        plus = Plus(tgt, child.getSymbol())
        plus.setParsedChildNames([child.name])
        self.addRule(plus)
        return plus

    def star(self, typ: str or None, child: Named) -> Rule:
        tgt = self.newOrExistingNonTerminal(typ)
        star = Star(tgt, child.getSymbol())
        star.setParsedChildNames([child.name])
        self.addRule(star)
        return star

    def orrule(self, typ: str or None, options: List[Named]) -> Rule:
        tgt = self.newOrExistingNonTerminal(typ)
        orrule = Or(tgt, EBNFCore.getSymbols(options))
        orrule.setParsedChildNames(EBNFCore.getNames(options))
        self.addRule(orrule)
        return orrule

    def optional(self, typ: str or None, child: Named) -> Rule:
        tgt = self.newOrExistingNonTerminal(typ)
        optional = Optional(tgt, child.getSymbol())
        optional.setParsedChildNames([child.name])
        self.addRule(optional)
        return optional

    def repeatFromTo(self, typ: str or None, child: Named, rfrom: int, rto: int) -> Rule:
        tgt = self.newOrExistingNonTerminal(typ)
        repeat = Repeat(tgt, child.getSymbol(), rfrom, rto)
        repeat.setParsedChildNames([child.name])
        self.addRule(repeat)
        return repeat

    def repeatWithNames(self, typ: str or None, child: Named, names: List[str]) -> Rule:
        tgt = self.newOrExistingNonTerminal(typ)
        lowerUpper = len(names)
        repeat = Repeat(tgt, child.getSymbol(), lowerUpper, lowerUpper)
        repeat.setParsedChildNames(names)
        self.addRule(repeat)
        return repeat

    def repeat(self, typ: str or None, child: Named, names: List[str] = None, rfrom: int = -1, rto: int = -1) -> Rule:
        if names is not None:
            return self.repeatWithNames(typ, child, names)
        else:
            return self.repeatFromTo(typ, child, rfrom, rto)

    def joinWithRange(self,
                      typ: str or None,
                      child: Named,
                      jopen: Symbol or None,
                      jclose: Symbol or None,
                      delimiter: Symbol,
                      cardinality: Range,
                      onlyKeepEntries: bool = True) -> Rule:
        tgt = self.newOrExistingNonTerminal(typ)
        join = Join(tgt, child.getSymbol(), jopen, jclose, delimiter, cardinality)
        join.onlyKeepEntries = onlyKeepEntries
        join.setParsedChildNames([child.name])
        self.addRule(join)
        return join

    def joinWithNames(self,
                      typ: str or None,
                      child: Named,
                      jopen: Symbol or None,
                      jclose: Symbol or None,
                      delimiter: Symbol,
                      names: List[str],
                      onlyKeepEntries: bool = True) -> Rule:
        lowerUpper = len(names)
        tgt = self.newOrExistingNonTerminal(typ)
        join = Join(tgt, child.getSymbol(), jopen, jclose, delimiter, Range(lowerUpper))
        join.onlyKeepEntries = onlyKeepEntries
        join.setParsedChildNames(names)
        self.addRule(join)
        return join

    def join(self,
             typ: str or None,
             child: Named,
             jopen: Symbol or None,
             jclose: Symbol or None,
             delimiter: Symbol,
             onlyKeepEntries: bool = True,
             names: List[str] = None,
             cardinality: Range = None) -> Rule:
        if names is not None:
            return self.joinWithNames(typ, child, jopen, jclose, delimiter, names, onlyKeepEntries)
        else:
            return self.joinWithRange(typ, child, jopen, jclose, delimiter, cardinality, onlyKeepEntries)

    def list(self, typ: str or None, child: Named) -> Rule:
        wsStar = self.star(None, WHITESPACE.withName()).withName("ws*")
        delimiter = self.sequence(None, [
                                  wsStar,
                                  literal(",").withName(),
                                  wsStar])
        delimiter.setAutocompleter(Autocompleter(lambda pn, justCheck: Autocompletion.literal(pn, [""] if len(pn.getParsedString()) > 0 else [", "])))
        return self.joinWithRange(typ, child, None, None, delimiter.tgt, STAR)

    def tuple(self, typ: str or None, child: Named, names: List[str]) -> Rule:
        wsStar = self.star(None, WHITESPACE.withName()).withName("ws*")
        wsStar.get().setAutocompleter(Autocompleter(lambda pn, justCheck: Autocompletion.literal(pn, [""])))
        jopen: Rule = self.sequence(None, [literal("(").withName("open"), wsStar])
        jclose: Rule = self.sequence(None, [wsStar, literal(")").withName("close")])
        delimiter: Rule = self.sequence(None, [wsStar, literal(",").withName("delimiter"), wsStar])
        ret: Rule = self.joinWithNames(typ, child, jopen.tgt, jclose.tgt, delimiter.tgt, names=names)

        def getAutocompletion(pn: ParsedNode, justCheck: bool) -> str or None:
            if len(pn.getParsedString()) > 0:
                return None
            if justCheck:
                return Autocompletion.doesAutocomplete(pn)

            seq = EntireSequence(pn)
            seq.addLiteral(jopen.tgt, "open", "(")
            seq.addParameterized(child.getSymbol(), names[0], names[0])
            for idx in range(1, len(names)):
                name = names[idx]
                seq.addLiteral(delimiter.tgt, "delimiter", ", ")
                seq.addParameterized(child.getSymbol(), name, name)
            seq.addLiteral(jclose.tgt, "close", ")")
            return seq.asArray()

        ret.setAutocompleter(Autocompleter(getAutocompletion))
        return ret

    def makeCharacterClass(self, name: str or None, pattern: str) -> Rule:
        ret: Rule = self.sequence(name, [characterClass(pattern).withName("character-class")])
        ret.setEvaluator(Evaluator(lambda pn: pn.getParsedString("character-class")[0]))
        ret.setAutocompleter(DEFAULT_INLINE_AUTOCOMPLETER)
        return ret

    def sequence(self, typ: str or None, children: List[Named]) -> Rule:
        tgt = self.newOrExistingNonTerminal(typ)
        sequence = Sequence(tgt, EBNFCore.getSymbols(children))
        sequence.setParsedChildNames(EBNFCore.getNames(children))
        self.addRule(sequence)
        return sequence

    @staticmethod
    def getSymbols(named: List[Named]) -> List[Symbol]:
        return list(map(lambda x: x.getSymbol(), named))

    @staticmethod
    def getNames(named: List[Named]) -> List[str]:
        return list(map(lambda x: x.name, named))

    def addRule(self, rule: Rule) -> None:
        if rule.tgt.symbol not in self._symbols:
            self._symbols[rule.tgt.symbol] = rule.tgt
        for s in rule.children:
            if not s.isEpsilon() and s.symbol not in self._symbols:
                self._symbols[s.symbol] = s
        self._rules.append(rule)
        self._compiled = False

    def removeRules(self, symbol: NonTerminal):
        for i in range(len(self._rules) - 1, -1, -1):
            if self._rules[i].tgt == symbol:
                del(self._rules[i])
        self._compiled = True

    def newOrExistingNonTerminal(self, typ: str) -> NonTerminal or None:
        if typ is None:
            return None
        s = self.getSymbol(typ)
        if s is None:
            s = NonTerminal(typ)
        return cast(NonTerminal, s)
