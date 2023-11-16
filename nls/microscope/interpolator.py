from typing import Callable

Getter = Callable[[], float]
Setter = Callable[[int, float], None]


class Interpolator:
    def __init__(self, getter: Getter, setter: Setter, vTo: float, nCycles: int):
        self._getter = getter
        self._setter = setter
        self._vTo = vTo
        self._nCycles = nCycles
        self._vFrom: float = 0

    def _initialize(self):
        self._vFrom = self._getter()

    def interpolate(self, cycle: int) -> None:
        if cycle == 0:
            self._initialize()
        interpolated: float = self._vFrom + (cycle + 1) * (self._vTo - self._vFrom) / self._nCycles
        self._setter(cycle, interpolated)


def main():
    nCycles: int = 10
    interpolator: Interpolator = Interpolator(
        lambda: 5, lambda c, v: print(str(c) + ": " + str(v)), vTo=15, nCycles=nCycles)

    for i in range(nCycles):
        interpolator.interpolate(i)


if __name__ == "__main__":
    main()
