from nls.core import parsednodefactory
from nls.core.bnf import BNF
from nls.core.lexer import Lexer
from nls.core.nonterminal import NonTerminal
from nls.core.parsingstate import ParsingState
from nls.core.production import Production
from nls.core.rdparser import RDParser
from nls.core.terminal import literal, DIGIT


def assertEquals(exp, real):
    if exp != real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def assertNotEquals(exp, real):
    if exp == real:
        raise Exception("Expected " + str(exp) + ", but got " + str(real))


def testParse():
    bnf = BNF()
    bnf.addProduction(Production(NonTerminal("EXPR"), [
        NonTerminal("TERM"), literal("+"), NonTerminal("EXPR")]))
    bnf.addProduction(Production(NonTerminal("EXPR"), [
        NonTerminal("TERM")]))
    bnf.addProduction(Production(NonTerminal("TERM"), [
        NonTerminal("FACTOR"), literal("*"), NonTerminal("FACTOR")]))
    bnf.addProduction(Production(NonTerminal("TERM"), [
        NonTerminal("FACTOR")]))
    bnf.addProduction(Production(NonTerminal("FACTOR"), [
        DIGIT]))

    bnf.addProduction(Production(BNF.ARTIFICIAL_START_SYMBOL, [
        NonTerminal("EXPR"), BNF.ARTIFICIAL_STOP_SYMBOL]))

    parser = RDParser(bnf, Lexer("3+4*6+8"), parsednodefactory.DEFAULT)
    parsed = parser.parse()
    assertEquals(ParsingState.SUCCESSFUL, parsed.matcher.state)


if __name__ == "__main__":
    testParse()