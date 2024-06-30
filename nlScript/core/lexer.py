class Lexer:
    def __init__(self, input: str):
        self._input = input
        self._pos = 0

    @property
    def pos(self) -> int:
        return self._pos

    @pos.setter
    def pos(self, pos: int) -> None:
        self._pos = pos

    def fwd(self, inc: int) -> None:
        self._pos += inc

    def peek(self, n=0) -> str or None:
        p = self._pos + n
        if p < len(self._input):
            return self._input[p]
        return '$'

    def substring(self, fr: int, to: int = -1) -> str:
        if to == -1:
            return self._input[fr:]
        return self._input[fr:to]

    def isDone(self) -> bool:
        return self._pos > len(self._input)

    def isAtEnd(self, fwd: int = 0) -> bool:
        return self._pos + fwd == len(self._input)

    def __str__(self) -> str:
        return self._input[0: self._pos] + " -- " + self._input[self._pos:]


if __name__ == '__main__':
    lexer = Lexer("This is a test")
    print(lexer.substring(3))
    print(lexer.substring(3, 7))
