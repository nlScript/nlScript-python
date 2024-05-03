from __future__ import annotations
from typing import TYPE_CHECKING, Callable

from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from nls.parsednode import ParsedNode


class IEvaluator(ABC):
    @abstractmethod
    def evaluate(self, pn: ParsedNode) -> object:
        pass


class Evaluator(IEvaluator):
    def __init__(self, evaluate: Callable[[ParsedNode], object]):
        self._evaluate = evaluate

    def evaluate(self, pn: ParsedNode) -> object:
        return self._evaluate(pn)


class DefaultEvaluator(IEvaluator):
    def evaluate(self, pn: ParsedNode) -> object:
        return pn.getParsedString()


class AllChildrenEvaluator(IEvaluator):
    def evaluate(self, pn: ParsedNode) -> object:
        if len(pn.children) == 0:
            return list()

        return list(map(lambda ch: ch.evaluate(), pn.children))


class FirstChildEvaluator(IEvaluator):
    def evaluate(self, pn: ParsedNode) -> object:
        return pn.evaluate(0)


ALL_CHILDREN_EVALUATOR = AllChildrenEvaluator()

FIRST_CHILD_EVALUATOR = FirstChildEvaluator()

DEFAULT_EVALUATOR = DefaultEvaluator()
