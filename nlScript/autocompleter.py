from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, Dict, cast

from abc import ABC, abstractmethod

from nlScript.core.autocompletion import Autocompletion, EntireSequence, Purpose
from nlScript.core.bnf import BNF
from nlScript.core.defaultparsednode import DefaultParsedNode
from nlScript.core.lexer import Lexer
from nlScript.core.production import Production
from nlScript.core.symbol import Symbol
from nlScript.ebnf import ebnfparsednodefactory
from nlScript.ebnf.sequence import Sequence
from nlScript.util.completepath import CompletePath
from nlScript.parsednode import ParsedNode

if TYPE_CHECKING:
    from nlScript.ebnf.ebnfcore import EBNFCore


class IAutocompleter(ABC):
    @abstractmethod
    def getAutocompletion(self, pn: DefaultParsedNode, justCheck: bool) -> List[Autocompletion] or None:
        pass


class Autocompleter(IAutocompleter):
    def __init__(self, getAutocompletion: Callable[[ParsedNode, bool], List[Autocompletion]]):
        self._getAutocompletion = getAutocompletion

    def getAutocompletion(self, pn: ParsedNode, justCheck: bool) -> List[Autocompletion] or None:
        return self._getAutocompletion(pn, justCheck)


class DefaultInlineAutocompleter(IAutocompleter):
    def getAutocompletion(self, pn: DefaultParsedNode, justCheck: bool) -> List[Autocompletion] or None:
        alreadyEntered = pn.getParsedString()
        if len(alreadyEntered) > 0:
            return Autocompletion.veto(pn)
        name = pn.name
        if name is None:
            name = pn.symbol.symbol
        if name is None:
            return None
        return Autocompletion.parameterized(pn, name)


class EntireSequenceAutocompleter(IAutocompleter):
    calledNTimes = 0

    def __init__(self, ebnf: EBNFCore, symbol2Autocompletion: Dict[str, List[Autocompletion]]):
        self._ebnf = ebnf
        self._symbol2Autocompletion = symbol2Autocompletion

    def getAutocompletion(self, pn: DefaultParsedNode, justCheck: bool) -> List[Autocompletion] or None:
        EntireSequenceAutocompleter.calledNTimes += 1
        import nlScript.core.rdparser
        alreadyEntered = pn.getParsedString()

        sequence = cast(ParsedNode, pn).getRule()
        children: List[Symbol] = sequence.children

        entireSequenceCompletion = EntireSequence(pn)

        for idx, child in enumerate(children):
            key = child.symbol + ":" + sequence.getNameForChild(idx)
            try:
                autocompletionsForChild = self._symbol2Autocompletion[key]
                entireSequenceCompletion.add(autocompletionsForChild)
                continue
            except KeyError:
                pass

            bnf = self._ebnf.getBNF().copy()
            newSequence = Sequence(None, [child])
            newSequence.setParsedChildNames([sequence.getNameForChild(idx)])
            newSequence.createBNF(bnf)

            bnf.removeStartProduction()
            bnf.addProduction(Production(BNF.ARTIFICIAL_START_SYMBOL, [newSequence.tgt]))
            parser = nlScript.core.rdparser.RDParser(bnf, Lexer(""), ebnfparsednodefactory.INSTANCE)

            autocompletionsForChild = []
            parser.parse(autocompletionsForChild)

            self._symbol2Autocompletion[key] = autocompletionsForChild
            entireSequenceCompletion.add(autocompletionsForChild)

        # avoid to call getCompletion() more often than necessary
        if len(alreadyEntered) == 0:
            return entireSequenceCompletion.asArray()

        try:
            idx = entireSequenceCompletion.getCompletion(Purpose.FOR_INSERTION).index("${")
        except ValueError:
            return entireSequenceCompletion.asArray()

        if len(alreadyEntered) > idx:
            return None

        return entireSequenceCompletion.asArray()


class PathAutocompleter(IAutocompleter):
    def __init__(self):
        pass

    def getAutocompletion(self, pn: DefaultParsedNode, justCheck: bool) -> List[Autocompletion] or None:
        if justCheck:
            return Autocompletion.doesAutocomplete(pn)
        completion: List[str] = CompletePath.getCompletion(pn.getParsedString())
        return Autocompletion.literal(pn, completion)


DEFAULT_INLINE_AUTOCOMPLETER = DefaultInlineAutocompleter()


PATH_AUTOCOMPLETER = PathAutocompleter()
