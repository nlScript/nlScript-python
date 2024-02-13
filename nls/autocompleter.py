from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, Dict

from abc import ABC, abstractmethod

from nls.core.autocompletion import Autocompletion
from nls.core.bnf import BNF
from nls.core.lexer import Lexer
from nls.core.production import Production
from nls.core.symbol import Symbol
from nls.ebnf import ebnfparsednodefactory
from nls.ebnf.sequence import Sequence
from nls.util.completepath import CompletePath

if TYPE_CHECKING:
    from nls.parsednode import ParsedNode
    from nls.ebnf.ebnfcore import EBNFCore


class IAutocompleter(ABC):
    VETO = "VETO"

    DOES_AUTOCOMPLETE = "DOES_AUTOCOMPLETE"

    @abstractmethod
    def getAutocompletion(self, pn: ParsedNode, justCheck: bool) -> str or None:
        pass


class Autocompleter(IAutocompleter):
    def __init__(self, getAutocompletion: Callable[[ParsedNode, bool], str]):
        self._getAutocompletion = getAutocompletion

    def getAutocompletion(self, pn: ParsedNode, justCheck: bool) -> str or None:
        return self._getAutocompletion(pn, justCheck)


class IfNothingYetEnteredAutocompleter(IAutocompleter):
    def __init__(self, completion: str):
        self._completion = completion

    # override abstract method
    def getAutocompletion(self, pn: ParsedNode, justCheck: bool) -> str or None:
        return self._completion if len(pn.getParsedString()) == 0 else ""


class DefaultInlineAutocompleter(IAutocompleter):
    def getAutocompletion(self, pn: ParsedNode, justCheck: bool) -> str or None:
        alreadyEntered = pn.getParsedString()
        if len(alreadyEntered) > 0:
            return IAutocompleter.VETO
        name = pn.name
        if name is not None:
            return "${" + name + "}"
        name = pn.symbol.symbol
        if name is not None:
            return "${" + name + "}"
        return None


class EmptyAutocompleter(IAutocompleter):
    def getAutocompletion(self, pn: ParsedNode, justCheck: bool) -> str or None:
        return ""


class EntireSequenceAutocompleter(IAutocompleter):
    calledNTimes = 0

    def __init__(self, ebnf: EBNFCore, symbol2Autocompletion: Dict[str, str]):
        self._ebnf = ebnf
        self._symbol2Autocompletion = symbol2Autocompletion

    def getAutocompletion(self, pn: ParsedNode, justCheck: bool) -> str or None:
        EntireSequenceAutocompleter.calledNTimes += 1
        import nls.core.rdparser
        alreadyEntered = pn.getParsedString()
        # if len(alreadyEntered) > 0:
        #     return Autocompleter.VETO

        if justCheck:
            return Autocompleter.DOES_AUTOCOMPLETE

        autocompletionString = ""
        sequence = pn.getRule()
        children: List[Symbol] = sequence.children

        for idx, child in enumerate(children):
            key = child.symbol + ":" + sequence.getNameForChild(idx)
            autocompletionStringForChild = None
            try:
                autocompletionStringForChild = self._symbol2Autocompletion[key]
                autocompletionString += autocompletionStringForChild
                continue
            except KeyError:
                pass

            bnf = self._ebnf.getBNF().copy()
            newSequence = Sequence(None, [child])
            newSequence.setParsedChildNames([sequence.getNameForChild(idx)])
            newSequence.createBNF(bnf)

            bnf.removeStartProduction()
            bnf.addProduction(Production(BNF.ARTIFICIAL_START_SYMBOL, [newSequence.tgt]))
            parser = nls.core.rdparser.RDParser(bnf, Lexer(""), ebnfparsednodefactory.INSTANCE)

            autocompletions: List[Autocompletion] = []
            parser.parse(autocompletions)
            nA = len(autocompletions)
            if nA > 1:
                autocompletionStringForChild = "${" + sequence.getNameForChild(idx) + "}"
            elif nA == 1:
                autocompletionStringForChild = autocompletions[0].completion

            self._symbol2Autocompletion[key] = autocompletionStringForChild
            autocompletionString += autocompletionStringForChild

        try:
            idx = autocompletionString.index("${")
        except ValueError:
            return autocompletionString

        if len(alreadyEntered) > idx:
            return Autocompleter.VETO

        return autocompletionString


class PathAutocompleter(IAutocompleter):
    def __init__(self):
        pass

    def getAutocompletion(self, pn: ParsedNode, justCheck: bool) -> str or None:
        if justCheck:
            return Autocompleter.DOES_AUTOCOMPLETE
        return CompletePath.getCompletion(pn.getParsedString())


DEFAULT_INLINE_AUTOCOMPLETER = DefaultInlineAutocompleter()


EMPTY_AUTOCOMPLETER = EmptyAutocompleter()


PATH_AUTOCOMPLETER = PathAutocompleter()
