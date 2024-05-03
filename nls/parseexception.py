from __future__ import annotations

from typing import TYPE_CHECKING, List

from nls.core.lexer import Lexer

if TYPE_CHECKING:
    from nls.core.defaultparsednode import DefaultParsedNode
    from nls.core.bnf import BNF
    from nls.core.autocompletion import Autocompletion, Purpose
    from nls.core.rdparser import RDParser


class ParseException(Exception):
    def __init__(self, root: DefaultParsedNode, failedTerminal: DefaultParsedNode, parser: RDParser):
        super().__init__()
        self._root = root
        self._failedTerminal = failedTerminal
        self._parser = parser

        tmp: DefaultParsedNode = failedTerminal
        while tmp is not None and not tmp.doesAutocomplete():
            tmp = tmp.parent
        self._firstAutocompletingAncestorThatFailed = tmp

    def getMessage(self) -> str:
        return self.getError()

    def getRoot(self) -> DefaultParsedNode:
        return self._root

    def getFailedTerminal(self) -> DefaultParsedNode:
        return self._failedTerminal

    def getFirstAutocompletingAncestorThatFailed(self) -> DefaultParsedNode:
        return self._firstAutocompletingAncestorThatFailed

    def getError(self) -> str:
        from nls.core.rdparser import RDParser

        lexer: Lexer = self._parser.getLexer()
        grammar: BNF = self._parser.getGrammar()

        errorPos: int = self._failedTerminal.matcher.pos + len(self._failedTerminal.matcher.parsed) - 1

        # the character at last.matcher.pos failed, everything before must have been working
        workingText: str = lexer.substring(0, self._failedTerminal.matcher.pos)
        # create a new parser and collect the autocompletions
        workingLexer = Lexer(workingText)
        parser2 = RDParser(grammar, workingLexer, self._parser.getParsedNodeFactory())
        expectations: List[Autocompletion] = []
        try:
            parser2.parse(expectations)
        except ParseException:
            return "Error at position " + str(errorPos)

        lines: List[str] = lexer.substring(0, errorPos + 1).splitlines()
        errorLine: int = len(lines) - 1
        errorPosInLastLine = len(lines[errorLine]) - 1

        nl = "\n"
        errorMessage = "Error at position " + str(errorPos) + " in line " + str(errorLine) + ":" + nl
        errorMessage += lines[errorLine] + nl
        for i in range(errorPosInLastLine):
            errorMessage += " "
        errorMessage += "^" + nl

        exString: List[str] = list(map(lambda ac: ac.getCompletion(Purpose.FOR_INSERTION), expectations))
        errorMessage += "Expected " + str(exString)

        return errorMessage



