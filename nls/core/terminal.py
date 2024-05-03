from __future__ import annotations

from abc import abstractmethod
from collections import Counter

from nls.core.named import Named
from nls.core.symbol import Symbol
from nls.core.lexer import Lexer
from nls.core.matcher import Matcher
from nls.core.parsingstate import ParsingState


class Terminal(Symbol):

    def __init__(self, symbol: str):
        super().__init__(symbol)

    # implement abstract method
    def isTerminal(self) -> bool:
        return True

    # implement abstract method
    def isNonTerminal(self) -> bool:
        return False

    # implement abstract method
    def isEpsilon(self) -> bool:
        return False

    @abstractmethod
    def matches(self, lexer: Lexer) -> Matcher:
        pass

    @abstractmethod
    def evaluate(self, matcher: Matcher) -> object:
        pass

    def withName(self, name: str = None):
        return Named[Terminal](self, name)


class Epsilon(Terminal):
    def __init__(self):
        super().__init__("epsilon")

    def isEpsilon(self) -> bool:
        return True

    # override abstract method
    def matches(self, lexer: Lexer) -> Matcher:
        return Matcher(ParsingState.SUCCESSFUL, lexer.pos, "")

    def evaluate(self, matcher: Matcher) -> object:
        return None


class EndOfInput(Terminal):
    def __init__(self):
        super().__init__("EOI")

    # override abstract method
    def matches(self, lexer: Lexer) -> Matcher:
        pos = lexer.pos
        if lexer.isAtEnd():
            return Matcher(ParsingState.SUCCESSFUL, pos, " ")
        return Matcher(ParsingState.FAILED, pos, "")

    def evaluate(self, matcher: Matcher) -> object:
        return None


class Digit(Terminal):
    def __init__(self):
        super().__init__("digit")

    # override abstract method
    def matches(self, lexer: Lexer) -> Matcher:
        pos = lexer.pos
        if lexer.isAtEnd():
            return Matcher(ParsingState.END_OF_INPUT, pos, "")
        c = lexer.peek()
        if c.isdigit():
            return Matcher(ParsingState.SUCCESSFUL, pos, c)
        return Matcher(ParsingState.FAILED, pos, c)

    def evaluate(self, matcher: Matcher) -> object:
        return matcher.parsed[0]


class Literal(Terminal):
    def __init__(self, symbol: str):
        super().__init__(symbol)

    # override abstract method
    def matches(self, lexer: Lexer) -> Matcher:
        pos = lexer.pos
        symbol = self.symbol
        for i in range(len(symbol)):
            if lexer.isAtEnd(i):
                return Matcher(ParsingState.END_OF_INPUT, pos, lexer.substring(pos, pos + i + 1))
            if lexer.peek(i) != symbol[i]:
                return Matcher(ParsingState.FAILED, pos, lexer.substring(pos, pos + i + 1))

        return Matcher(ParsingState.SUCCESSFUL, pos, symbol)

    def evaluate(self, matcher: Matcher) -> object:
        return matcher.parsed

    def __str__(self) -> str:
        return "'" + self._symbol + "'"


class Letter(Terminal):
    def __init__(self):
        super().__init__("letter")

    # override abstract method
    def matches(self, lexer: Lexer) -> Matcher:
        pos = lexer.pos
        if lexer.isAtEnd():
            return Matcher(ParsingState.END_OF_INPUT, pos, "")
        c = lexer.peek()
        if c.isalpha():
            return Matcher(ParsingState.SUCCESSFUL, pos, c)
        return Matcher(ParsingState.FAILED, pos, c)

    def evaluate(self, matcher: Matcher) -> object:
        return matcher.parsed[0]


class Whitespace(Terminal):
    def __init__(self):
        super().__init__("whitespace")

    # override abstract method
    def matches(self, lexer: Lexer) -> Matcher:
        pos = lexer.pos
        if lexer.isAtEnd():
            return Matcher(ParsingState.END_OF_INPUT, pos, "")
        c = lexer.peek()
        if c == ' ' or c == '\t':
            return Matcher(ParsingState.SUCCESSFUL, pos, c)
        return Matcher(ParsingState.FAILED, pos, c)

    def evaluate(self, matcher: Matcher) -> object:
        return matcher.parsed[0]


class CharacterClass(Terminal):
    def __init__(self, pattern: str):
        super().__init__(pattern)

        b = pattern.strip()
        if len(b) == 0:
            raise Exception("empty character class pattern")
        if b[0] != '[' or b[-1] != ']':
            raise Exception("Wrong character class format: " + pattern)

        start = 1
        end = len(b) - 2

        negated = b[1] == '^'
        if negated:
            start = start + 1

        self._ranges = Ranges(negated)

        if b[start] == '-':
            self._ranges.add(SingleCharacterRange(ord('-')))
            start = start + 1

        if b[end] == '-':
            self._ranges.add(SingleCharacterRange(ord('-')))
            end = end - 1

        idx = start
        while idx <= end:
            nIdx = idx + 1
            c = b[idx]
            if nIdx <= end and b[nIdx] == '-':
                u = b[idx + 2]
                if c == '-' or u == '-':
                    raise Exception("Wrong character class format: " + pattern)
                self._ranges.add(CharacterRange(ord(c), ord(u)))
                idx = idx + 3
            else:
                self._ranges.add(SingleCharacterRange(ord(c)))
                idx = idx + 1

    # override abstract method
    def matches(self, lexer: Lexer) -> Matcher:
        pos = lexer.pos
        if lexer.isAtEnd():
            return Matcher(ParsingState.END_OF_INPUT, pos, "")
        c = lexer.peek()
        if self._ranges.checkCharacter(ord(c)):
            return Matcher(ParsingState.SUCCESSFUL, pos, c)
        return Matcher(ParsingState.FAILED, pos, c)

    def evaluate(self, matcher: Matcher) -> object:
        return matcher.parsed[0]


class CharacterRange:
    def __init__(self, lower: int, upper: int):
        self._lower = lower
        self._upper = upper

    @property
    def lower(self) -> int:
        return self._lower

    @property
    def upper(self) -> int:
        return self._upper

    def checkCharacter(self, i: int) -> bool:
        return self.lower <= i <= self.upper

    def __eq__(self, other: CharacterRange) -> bool:
        if type(self) != type(other):
            return False
        return self.lower == other.lower and self.upper == other.upper

    def __ne__(self, other: CharacterRange) -> bool:
        return not self == other


class SingleCharacterRange(CharacterRange):
    def __init__(self, number: int):
        super().__init__(number, number)
        self._number = number

    # override
    def checkCharacter(self, i: int) -> bool:
        return self._number == i


class Ranges:
    def __init__(self, negated: bool):
        self._negated = negated
        self._ranges = []

    @property
    def ranges(self):
        return self._ranges

    def add(self, arange: CharacterRange) -> None:
        self._ranges.append(arange)

    def checkCharacter(self, i: int) -> bool:
        for ran in self._ranges:
            check = ran.checkCharacter(i)
            if not self._negated and check:
                return True
            if self._negated and check:
                return False

        return self._negated

    def __eq__(self, other: Ranges) -> bool:
        if type(self) != type(other):
            return False
        return Counter(self._ranges) == Counter(other.ranges)

    def __ne__(self, other: Ranges) -> bool:
        return not self == other


EPSILON = Epsilon()
DIGIT = Digit()
LETTER = Letter()
WHITESPACE = Whitespace()
END_OF_INPUT = EndOfInput()


def literal(s: str) -> Literal:
    return Literal(s)


def characterClass(pattern: str) -> CharacterClass:
    return CharacterClass(pattern)


if __name__ == "__main__":
    e = EPSILON
    print(str(e) + " matches 'lll'? " + str(e.matches(Lexer("lll"))))

    e = literal("bla blubb")
    print(str(e) + "matches 'bla blubb hahaha'? " + str(e.matches(Lexer("bla blubb hahaha"))))
    print(str(e) + "matches 'bla blurr hahaha'? " + str(e.matches(Lexer("bla blurr hahaha"))))

    e = characterClass("[A-Za-z]")
    print(str(e) + " matches 'abc'? " + str(e.matches(Lexer("abc"))))
    print(str(e) + " matches '1bc'? " + str(e.matches(Lexer("1bc"))))
