from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from nls.autocompleter import DEFAULT_INLINE_AUTOCOMPLETER, IfNothingYetEnteredAutocompleter, \
    EntireSequenceAutocompleter, PATH_AUTOCOMPLETER
from nls.core.terminal import literal, DIGIT, WHITESPACE, characterClass
from nls.ebnf.ebnfcore import EBNFCore
from nls.evaluator import Evaluator, DEFAULT_EVALUATOR
from nls.util.range import Range

if TYPE_CHECKING:
    from nls.ebnf.rule import Rule
    from nls.parsednode import ParsedNode


class EBNF(EBNFCore):
    SIGN_NAME = "sign"
    INTEGER_NAME = "int"
    FLOAT_NAME = "float"
    WHITESPACE_STAR_NAME = "whitespace-star"
    WHITESPACE_PLUS_NAME = "whitespace-plus"
    INTEGER_RANGE_NAME = "integer-range"
    PATH_NAME = "path"
    TIME_NAME = "time"
    COLOR_NAME = "color"

    def __init__(self, other: EBNF = None):
        super().__init__(other)
        self.SIGN            = self.makeSign()           if other is None else other.SIGN
        self.INTEGER         = self.makeInteger()        if other is None else other.INTEGER
        self.FLOAT           = self.makeFloat()          if other is None else other.FLOAT
        self.WHITESPACE_STAR = self.makeWhitespaceStar() if other is None else other.WHITESPACE_STAR
        self.WHITESPACE_PLUS = self.makeWhitespacePlus() if other is None else other.WHITESPACE_PLUS
        self.INTEGER_RANGE   = self.makeIntegerRange()   if other is None else other.INTEGER_RANGE
        self.PATH            = self.makePath()           if other is None else other.PATH
        self.TIME            = self.makeTime()           if other is None else other.TIME
        self.COLOR           = self.makeColor()          if other is None else other.COLOR

    @staticmethod
    def clearFilesystemCache():
        PATH_AUTOCOMPLETER.clearFilesystemCache()

    def makeSign(self):
        return self.orrule(EBNF.SIGN_NAME,
                           [
                               literal("-").withName(),
                               literal("+").withName()
                           ])

    def makeInteger(self) -> Rule:
        # int -> (-|+)?digit+
        ret = self.sequence(EBNF.INTEGER_NAME, [
                            self.optional(None, self.SIGN.withName("sign")).withName("optional"),
                            self.plus(None, DIGIT.withName("digit")).withName("plus")])

        ret.setEvaluator(Evaluator(lambda pn: int(pn.getParsedString())))
        ret.setAutocompleter(DEFAULT_INLINE_AUTOCOMPLETER)
        return ret

    def makeFloat(self) -> Rule:
        # float -> (-|+)?digit+(.digit*)?
        ret = self.sequence(EBNF.FLOAT_NAME,
                            [
                                self.optional(None, self.SIGN.withName()).withName(),
                                self.plus(None, DIGIT.withName()).withName(),
                                self.optional(
                                    None,
                                    self.sequence(
                                        None,
                                        [
                                            literal(".").withName(),
                                            self.star(None, DIGIT.withName()).withName("star")
                                        ]).withName("sequence")
                                  ).withName()
                            ])

        ret.setEvaluator(Evaluator(lambda pn: float(pn.getParsedString())))
        ret.setAutocompleter(DEFAULT_INLINE_AUTOCOMPLETER)
        return ret

    def makeWhitespaceStar(self) -> Rule:
        ret = self.star(EBNF.WHITESPACE_STAR_NAME, WHITESPACE.withName())
        ret.setAutocompleter(IfNothingYetEnteredAutocompleter(" "))
        return ret

    def makeWhitespacePlus(self) -> Rule:
        ret = self.plus(EBNF.WHITESPACE_PLUS_NAME, WHITESPACE.withName())
        ret.setAutocompleter(IfNothingYetEnteredAutocompleter(" "))
        return ret

    def makeIntegerRange(self) -> Rule:
        delimiter = self.sequence(None, [
            self.WHITESPACE_STAR.withName("ws*"),
            literal("-").withName(),
            self.WHITESPACE_STAR.withName("ws*")])
        ret = self.joinWithNames(self.INTEGER_RANGE_NAME,
                                 self.INTEGER.withName(),
                                 None,
                                 None,
                                 delimiter.tgt,
                                 ["from", "to"])

        def evaluate(pn: ParsedNode) -> object:
            return Range(
                int(pn.evaluateChildByIndex(0)),
                int(pn.evaluateChildByIndex(1)))
        ret.setEvaluator(Evaluator(evaluate))
        return ret

    def makeColor(self) -> Rule:
        black       = self.sequence(None, [literal("black"       ).withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(  0,   0,   0)))
        white       = self.sequence(None, [literal("white"       ).withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(255, 255, 255)))
        red         = self.sequence(None, [literal("red"         ).withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(255,   0,   0)))
        orange      = self.sequence(None, [literal("orange"      ).withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(255, 128,   0)))
        yellow      = self.sequence(None, [literal("yellow"      ).withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(255, 255,   0)))
        lawngreen   = self.sequence(None, [literal("lawn green"  ).withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(128, 255,   0)))
        green       = self.sequence(None, [literal("green"       ).withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(  0, 255,   0)))
        springgreen = self.sequence(None, [literal("spring green").withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(  0, 255, 180)))
        cyan        = self.sequence(None, [literal("cyan"        ).withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(  0, 255, 255)))
        azure       = self.sequence(None, [literal("azure"       ).withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(  0, 128, 255)))
        blue        = self.sequence(None, [literal("blue"        ).withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(  0,   0, 255)))
        violet      = self.sequence(None, [literal("violet"      ).withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(128,   0, 255)))
        magenta     = self.sequence(None, [literal("magenta"     ).withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(255,   0, 255)))
        pink        = self.sequence(None, [literal("pink"        ).withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(255,   0, 128)))
        gray        = self.sequence(None, [literal("gray"        ).withName()]).setEvaluator(Evaluator(lambda pn: EBNF.rgb2int(128, 128, 128)))

        custom = self.tuple(None, self.INTEGER.withName(), ["red", "green", "blue"])

        return self.orrule(self.COLOR_NAME, [
                custom.withName(),
                black.withName(),
                white.withName(),
                red.withName(),
                orange.withName(),
                yellow.withName(),
                lawngreen.withName(),
                green.withName(),
                springgreen.withName(),
                cyan.withName(),
                azure.withName(),
                blue.withName(),
                violet.withName(),
                magenta.withName(),
                pink.withName(),
                gray.withName()])

    @staticmethod
    def rgb2int(r: int, g: int, b: int) -> int:
        return (0xff << 24) | ((r & 0xff) << 16) | ((g & 0xff) << 8) | (b & 0xff)

    def makeTime(self) -> Rule:
        ret = self.sequence(self.TIME_NAME, [
                            self.optional(None, DIGIT.withName()).withName(),
                            DIGIT.withName(),
                            literal(":").withName(),
                            DIGIT.withName(),
                            DIGIT.withName()
                            ])
        ret.setEvaluator(Evaluator(lambda pn: datetime.datetime.strptime(pn.getParsedString(), '%H:%M').time()))
        ret.setAutocompleter(IfNothingYetEnteredAutocompleter("${HH}:${MM}"))
        return ret

    def makePath(self) -> Rule:
        innerPath = self.plus(None, characterClass("[^'<>|?*\n]").withName("inner-path"))
        innerPath.setEvaluator(DEFAULT_EVALUATOR)
        innerPath.setAutocompleter(PATH_AUTOCOMPLETER)

        path = self.sequence(EBNF.PATH_NAME, [
                             literal("'").withName(),
                             innerPath.withName("path"),
                             literal("'").withName()])
        path.setEvaluator(Evaluator(lambda pn: pn.evaluateChildByNames("path")))
        path.setAutocompleter(EntireSequenceAutocompleter(self, {}))
        return path
