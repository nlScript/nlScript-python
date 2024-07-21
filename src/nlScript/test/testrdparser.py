from nlScript.core import parsednodefactory
from nlScript.core.bnf import BNF
from nlScript.core.lexer import Lexer
from nlScript.core.nonterminal import NonTerminal
from nlScript.core.parsingstate import ParsingState
from nlScript.core.production import Production
from nlScript.core.rdparser import RDParser
from nlScript.core.terminal import literal, DIGIT


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
