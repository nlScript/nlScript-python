from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from nls.autocompleter import DEFAULT_INLINE_AUTOCOMPLETER, \
    EntireSequenceAutocompleter, PATH_AUTOCOMPLETER, Autocompleter
from nls.core.autocompletion import Autocompletion
from nls.core.terminal import literal
import nls.core.terminal as terminal
from nls.ebnf.ebnfcore import EBNFCore
from nls.evaluator import Evaluator, DEFAULT_EVALUATOR
from nls.util.range import Range

if TYPE_CHECKING:
    from nls.ebnf.rule import Rule
    from nls.parsednode import ParsedNode


class EBNF(EBNFCore):
    DIGIT_NAME = terminal.DIGIT.symbol
    LETTER_NAME = terminal.LETTER.symbol
    SIGN_NAME = "sign"
    INTEGER_NAME = "int"
    FLOAT_NAME = "float"
    MONTH_NAME = "month"
    WEEKDAY_NAME = "weekday"
    WHITESPACE_STAR_NAME = "whitespace-star"
    WHITESPACE_PLUS_NAME = "whitespace-plus"
    INTEGER_RANGE_NAME = "integer-range"
    PATH_NAME = "path"
    TIME_NAME = "time"
    DATE_NAME = "date"
    DATETIME_NAME = "date-time"
    COLOR_NAME = "color"

    def __init__(self, other: EBNF = None):
        super().__init__(other)
        self.SIGN            = self.makeSign()           if other is None else other.SIGN
        self.INTEGER         = self.makeInteger()        if other is None else other.INTEGER
        self.FLOAT           = self.makeFloat()          if other is None else other.FLOAT
        self.MONTH           = self.makeMonth()          if other is None else other.MONTH
        self.WEEKDAY         = self.makeWeekday()        if other is None else other.WEEKDAY
        self.WHITESPACE_STAR = self.makeWhitespaceStar() if other is None else other.WHITESPACE_STAR
        self.WHITESPACE_PLUS = self.makeWhitespacePlus() if other is None else other.WHITESPACE_PLUS
        self.INTEGER_RANGE   = self.makeIntegerRange()   if other is None else other.INTEGER_RANGE
        self.PATH            = self.makePath()           if other is None else other.PATH
        self.TIME            = self.makeTime()           if other is None else other.TIME
        self.DATE            = self.makeDate()           if other is None else other.DATE
        self.DATETIME        = self.makeDatetime()       if other is None else other.DATETIME
        self.COLOR           = self.makeColor()          if other is None else other.COLOR
        super().symbols[self.DIGIT_NAME] = terminal.DIGIT
        super().symbols[self.LETTER_NAME] = terminal.LETTER

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
                            self.plus(None, terminal.DIGIT.withName("digit")).withName("plus")])

        ret.setEvaluator(Evaluator(lambda pn: int(pn.getParsedString())))
        ret.setAutocompleter(DEFAULT_INLINE_AUTOCOMPLETER)
        return ret

    def makeDatetime(self) -> Rule:
        ret: Rule = self.sequence(self.DATETIME_NAME, [
            self.DATE.withName("date"),
            literal(" ").withName(),
            self.TIME.withName("time")
        ])

        def evaluate(pn: ParsedNode) -> object:
            date = pn.evaluate("date")
            time = pn.evaluate("time")
            return datetime.datetime.combine(date, time)

        ret.setEvaluator(Evaluator(evaluate))
        ret.setAutocompleter(EntireSequenceAutocompleter(self, {}))
        return ret

    def makeFloat(self) -> Rule:
        # float -> (-|+)?digit+(.digit*)?
        ret = self.sequence(EBNF.FLOAT_NAME,
                            [
                                self.optional(None, self.SIGN.withName()).withName(),
                                self.plus(None, terminal.DIGIT.withName()).withName(),
                                self.optional(
                                    None,
                                    self.sequence(
                                        None,
                                        [
                                            literal(".").withName(),
                                            self.star(None, terminal.DIGIT.withName()).withName("star")
                                        ]).withName("sequence")
                                  ).withName()
                            ])

        ret.setEvaluator(Evaluator(lambda pn: float(pn.getParsedString())))
        ret.setAutocompleter(DEFAULT_INLINE_AUTOCOMPLETER)
        return ret

    def makeWhitespaceStar(self) -> Rule:
        ret = self.star(EBNF.WHITESPACE_STAR_NAME, terminal.WHITESPACE.withName())
        ret.setAutocompleter(Autocompleter(lambda pn, justCheck: Autocompletion.literal(pn, [" "] if len(pn.getParsedString()) == 0 else [""])))
        return ret

    def makeWhitespacePlus(self) -> Rule:
        ret = self.plus(EBNF.WHITESPACE_PLUS_NAME, terminal.WHITESPACE.withName())
        ret.setAutocompleter(Autocompleter(lambda pn, justCheck: Autocompletion.literal(pn, [" "] if len(pn.getParsedString()) == 0 else [""])))
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
        hour: Rule = self.sequence(None, [
                            self.optional(None, terminal.DIGIT.withName()).withName(),
                            terminal.DIGIT.withName(),
        ])
        hour.setAutocompleter(DEFAULT_INLINE_AUTOCOMPLETER)

        minute = self.sequence(None, [
                            terminal.DIGIT.withName(),
                            terminal.DIGIT.withName()
        ])
        minute.setAutocompleter(DEFAULT_INLINE_AUTOCOMPLETER)

        ret: Rule = self.sequence(self.TIME_NAME, [
            hour.withName("HH"),
            literal(":").withName(),
            minute.withName("MM")
        ])
        ret.setEvaluator(Evaluator(lambda pn: datetime.datetime.strptime(pn.getParsedString(), '%H:%M').time()))
        ret.setAutocompleter(EntireSequenceAutocompleter(self, {}))
        return ret

    def makeMonth(self) -> Rule:
        return self.orrule(self.MONTH_NAME, [
            self.sequence(None, [literal("January")  .withName()]).setEvaluator(Evaluator(lambda pn: 0)).withName("january"),
            self.sequence(None, [literal("February") .withName()]).setEvaluator(Evaluator(lambda pn: 1)).withName("february"),
            self.sequence(None, [literal("March")    .withName()]).setEvaluator(Evaluator(lambda pn: 2)).withName("march"),
            self.sequence(None, [literal("April")    .withName()]).setEvaluator(Evaluator(lambda pn: 3)).withName("april"),
            self.sequence(None, [literal("Mai")      .withName()]).setEvaluator(Evaluator(lambda pn: 4)).withName("mai"),
            self.sequence(None, [literal("June")     .withName()]).setEvaluator(Evaluator(lambda pn: 5)).withName("june"),
            self.sequence(None, [literal("July")     .withName()]).setEvaluator(Evaluator(lambda pn: 6)).withName("july"),
            self.sequence(None, [literal("August")   .withName()]).setEvaluator(Evaluator(lambda pn: 7)).withName("august"),
            self.sequence(None, [literal("September").withName()]).setEvaluator(Evaluator(lambda pn: 8)).withName("september"),
            self.sequence(None, [literal("October")  .withName()]).setEvaluator(Evaluator(lambda pn: 9)).withName("october"),
            self.sequence(None, [literal("November") .withName()]).setEvaluator(Evaluator(lambda pn: 10)).withName("november"),
            self.sequence(None, [literal("December") .withName()]).setEvaluator(Evaluator(lambda pn: 11)).withName("december"),
        ])

    def makeWeekday(self) -> Rule:
        return self.orrule(self.WEEKDAY_NAME, [
            self.sequence(None, [literal("Monday")   .withName()]).setEvaluator(Evaluator(lambda pn: 0)) .withName("monday"),
            self.sequence(None, [literal("Tuesday")  .withName()]).setEvaluator(Evaluator(lambda pn: 1)) .withName("tuesday"),
            self.sequence(None, [literal("Wednesday").withName()]).setEvaluator(Evaluator(lambda pn: 2)) .withName("wednesday"),
            self.sequence(None, [literal("Thursday") .withName()]).setEvaluator(Evaluator(lambda pn: 3)) .withName("thursday"),
            self.sequence(None, [literal("Friday")   .withName()]).setEvaluator(Evaluator(lambda pn: 4)) .withName("friday"),
            self.sequence(None, [literal("Saturday") .withName()]).setEvaluator(Evaluator(lambda pn: 5)) .withName("saturday"),
            self.sequence(None, [literal("Sunday")   .withName()]).setEvaluator(Evaluator(lambda pn: 6)) .withName("sunday")
        ])

    def makeDate(self) -> Rule:
        day: Rule = self.sequence(None, [
            self.optional(None, terminal.DIGIT.withName()).withName(),
            terminal.DIGIT.withName()
        ])
        day.setAutocompleter(DEFAULT_INLINE_AUTOCOMPLETER)

        year: Rule = self.sequence(None, [
            terminal.DIGIT.withName(),
            terminal.DIGIT.withName(),
            terminal.DIGIT.withName(),
            terminal.DIGIT.withName(),
        ])
        year.setAutocompleter(DEFAULT_INLINE_AUTOCOMPLETER)

        ret: Rule = self.sequence(self.DATE_NAME, [
            day.withName("day"),
            literal(" ").withName(),
            self.MONTH.withName("month"),
            literal(" ").withName(),
            year.withName("year")
        ])

        ret.setEvaluator(Evaluator(lambda pn: datetime.datetime.strptime(pn.getParsedString(), "%d %B %Y").date()))
        ret.setAutocompleter(EntireSequenceAutocompleter(self, dict()))
        return ret

    def makePath(self) -> Rule:
        innerPath = self.plus(None, terminal.characterClass("[^'<>|?*\n]").withName("inner-path"))
        innerPath.setEvaluator(DEFAULT_EVALUATOR)
        innerPath.setAutocompleter(PATH_AUTOCOMPLETER)

        path = self.sequence(EBNF.PATH_NAME, [
                             literal("'").withName(),
                             innerPath.withName("path"),
                             literal("'").withName()])
        path.setEvaluator(Evaluator(lambda pn: pn.evaluateChildByNames("path")))
        path.setAutocompleter(EntireSequenceAutocompleter(self, {}))
        return path
