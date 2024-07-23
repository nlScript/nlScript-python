from __future__ import annotations

from datetime import datetime, timedelta, date, time
from typing import List

from nlScript.autocompleter import Autocompleter
from nlScript.core.autocompletion import Autocompletion
from nlScript.ebnf.ebnfparser import ParseStartListener
from nlScript.ebnf.parselistener import ParseListener
from nlScript.microscope.interpolator import Interpolator
from nlScript.microscope.timeline import Timeline
from nlScript.microscope.microscope import Microscope, LED, LEDSetting, Channel, Position, Lens, MagnificationChanger, \
    Binning
from nlScript.parsednode import ParsedNode
from nlScript.parser import Parser


class LanguageControl:
    def __init__(self, microscope: Microscope | None = None):
        self._microscope = microscope if microscope is not None else Microscope()
        self._timeline = Timeline()
        self._globalStart: time = datetime.now().time()

    def reset(self):
        self._globalStart: time = datetime.now().time()
        self._microscope.reset()
        self._timeline.clear()

    def getTimeline(self) -> Timeline:
        return self._timeline

    def initParser(self):
        definedChannels = []
        definedRegions = []

        def clearChannelsAndRegions():
            definedChannels.clear()
            definedRegions.clear()

        parser = Parser()
        parser.addParseStartListener(ParseStartListener(clearChannelsAndRegions))

        parser.defineType("led", "385nm", lambda e: LED.LED_385)
        parser.defineType("led", "470nm", lambda e: LED.LED_470)
        parser.defineType("led", "567nm", lambda e: LED.LED_567)
        parser.defineType("led", "625nm", lambda e: LED.LED_625)

        parser.defineType("led-power", "{<led-power>:int}%",
                          lambda e: e.evaluate("<led-power>"),
                          True)
        parser.defineType("exposure-time", "{<exposure-time>:int}ms",
                          lambda e: e.evaluate("<exposure-time>"),
                          True)
        parser.defineType("led-setting", "{led-power:led-power} at {wavelength:led}",
                          lambda e: LEDSetting(e.evaluate("wavelength"), e.evaluate("led-power")),
                          True)
        parser.defineType("another-led-setting", ", {led-setting:led-setting}",
                          lambda e: e.evaluate("led-setting"),
                          True)

        parser.defineType("channel-name", "'{<name>:[A-Za-z0-9]:+}'",
                          lambda e: e.getParsedString("<name>"),
                          True)

        parser.defineSentence(
            "Define channel {channel-name:channel-name}:" +
            "{\n  }excite with {led-setting:led-setting}{another-led-setting:another-led-setting:0-3}" +
            "{\n  }use an exposure time of {exposure-time:exposure-time}.",
            lambda e: self._microscope.addChannel(
                Channel(
                    name=e.evaluate("channel-name"),
                    first=e.evaluate("led-setting"),
                    remaining=e.evaluate("another-led-setting"),
                    exposureTime=e.evaluate("exposure-time")))
        ).onSuccessfulParsed(ParseListener(lambda n: definedChannels.append(n.getParsedString("channel-name"))))

        # Define "Tile Scan 1" as a (w x h x d) region centered at (x, y, z)
        parser.defineType("region-name", "'{<region-name>:[a-zA-Z0-9]:+}'",
                          lambda e: e.getParsedString("<region-name>"),
                          True)

        parser.defineType("region-dimensions", "{<width>:float} x {<height>:float} x {<depth>:float} microns",
                          lambda e: [
                              e.evaluate("<width>"),
                              e.evaluate("<height>"),
                              e.evaluate("<depth>")],
                          True)

        parser.defineType("region-center", "{<center>:tuple<float,x,y,z>} microns",
                          lambda e: e.evaluate("<center>"),
                          True)

        parser.defineSentence(
            "Define a position {region-name:region-name}:" +
            "{\n  }{region-dimensions:region-dimensions}" +
            "{\n  }centered at {region-center:region-center}.",
            lambda e: self._microscope.addPosition(
                Position(
                    name=e.evaluate("region-name"),
                    center=e.evaluate("region-center"),
                    extent=e.evaluate("region-dimensions")))
        ).onSuccessfulParsed(ParseListener(lambda n: definedRegions.append(n.getParsedString("region-name"))))

        parser.defineSentence("Define the output folder at {folder:path}.", None)

        parser.defineType("defined-channels", "'{channel:[A-Za-z0-9]:+}'",
                          evaluator=lambda e: e.getParsedString("channel"),
                          autocompleter=lambda e, justCheck: Autocompletion.literal(e, definedChannels))

        parser.defineType("defined-positions", "'{position:[A-Za-z0-9]:+}'",
                          evaluator=lambda e: e.getParsedString("position"),
                          autocompleter=lambda e, justCheck: Autocompletion.literal(e, definedRegions))

        parser.defineType("time-unit", "second(s)", evaluator=lambda e: 1)
        parser.defineType("time-unit", "minute(s)", evaluator=lambda e: 60)
        parser.defineType("time-unit", "hour(s)",   evaluator=lambda e: 3600)

        parser.defineType("time-interval", "{n:float} {time-unit:time-unit}",
                          lambda e: round(
                              float(e.evaluate("n")) *         # n
                              int(e.evaluate("time-unit"))),  # unit
                          True)

        parser.defineType("repetition", "once", lambda e: [1, 0])
        parser.defineType("repetition", "every {interval:time-interval} for {duration:time-interval}",
                          lambda e: [e.evaluate("interval"), e.evaluate("duration")],
                          True)

        parser.defineType("z-distance", "{z-distance:float} microns",
                          lambda e: e.evaluate("z-distance"),
                          True)

        parser.defineType("lens", "5x lens",  lambda e: Lens.FIVE)
        parser.defineType("lens", "20x lens", lambda e: Lens.TWENTY)

        parser.defineType("mag", "0.5x magnification changer", lambda e: MagnificationChanger.ZERO_FIVE)
        parser.defineType("mag", "1.0x magnification changer", lambda e: MagnificationChanger.ONE_ZERO)
        parser.defineType("mag", "2.0x magnification changer", lambda e: MagnificationChanger.TWO_ZERO)

        parser.defineType("binning", "1 x 1", evaluator=lambda e: Binning.ONE)
        parser.defineType("binning", "2 x 2", evaluator=lambda e: Binning.TWO)
        parser.defineType("binning", "3 x 3", evaluator=lambda e: Binning.THREE)
        parser.defineType("binning", "4 x 4", evaluator=lambda e: Binning.FOUR)
        parser.defineType("binning", "5 x 5", evaluator=lambda e: Binning.FIVE)

        parser.defineType("start", "At the beginning", lambda e: self._globalStart)
        parser.defineType("start", "At {time:time}",   lambda e: e.evaluate("time"), True)
        parser.defineType("start", "After {delay:time-interval}",
                          lambda e: (datetime.combine(
                                  date.today(),
                                  self._globalStart
                              ) + timedelta(seconds=e.evaluate("delay"))).time(),
                          True)

        parser.defineType("position-list", "all positions", lambda e: [Microscope.ALL_POSITIONS])
        parser.defineType("position-list", "position(s) {positions:list<defined-positions>}",
                          lambda e: e.evaluate("positions"))

        parser.defineType("channel-list", "all channels", lambda e: [Microscope.ALL_CHANNELS])
        parser.defineType("channel-list", "channel(s) {channels:list<defined-channels>}",
                          lambda e: e.evaluate("channels"))

        def evaluateAcquisition(e: ParsedNode):
            tim: time = e.evaluate("start")
            repetition: List[int] = e.evaluate("repetition")
            interval: int = repetition[0]
            duration: int = repetition[1]

            positionNames: List[str] = e.evaluate("position-list")
            channelNames: List[str] = e.evaluate("channel-list")
            lens: Lens = e.evaluate("lens")
            mag: MagnificationChanger = e.evaluate("magnification")
            binning: Binning = e.evaluate("binning")
            dz: float = e.evaluate("dz")

            start: datetime = datetime.combine(date.today(), tim)
            if self._globalStart > tim:
                start = start + timedelta(days=1)

            nCycles: int = 1 if duration < interval else duration // interval + 1  # integer division
            for c in range(nCycles):
                plannedExecutionTime: datetime = start + timedelta(seconds=c * interval)

                def execute():
                    self._microscope.setLens(lens)
                    self._microscope.setMagnificationChanger(mag)
                    self._microscope.setBinning(binning)
                    self._microscope.acquire(positionNames, channelNames, dz)

                self._timeline.put(plannedExecutionTime, execute)

        parser.defineSentence(
            "{start:start}{, }acquire..." +
            "{\n  }{repetition:repetition}" +
            "{\n  }{position-list:position-list}" +
            "{\n  }{channel-list:channel-list}" +
            # "{\n  }with a resolution of {dx:float} x {dy:float} x {dz:float} microns.",
            "{\n  }with a plane distance of {dz:z-distance}" +
            "{\n  }using the {lens:lens} with the {magnification:mag} and a binning of {binning:binning}.",
            evaluateAcquisition)

        def enqueueInterpolator(plannedExecutionTime: datetime, interpolator: Interpolator, cycle: int):
            self._timeline.put(plannedExecutionTime, lambda: interpolator.interpolate(cycle))

        def evaluateAdjustLEDPower(e: ParsedNode):
            tim: time = e.evaluate("start")
            repetition: List[int] = e.evaluate("repetition")
            interval: int = repetition[0]
            duration: int = repetition[1]

            led: LED = e.evaluate("led")
            channel: str = e.evaluate("channel")
            power: int = e.evaluate("power")

            start: datetime = datetime.combine(date.today(), tim)
            if self._globalStart > tim:
                start = start + timedelta(days=1)

            nCycles: int = 1 if duration < interval else duration // interval + 1  # integer division

            interpolator: Interpolator = Interpolator(
                lambda: self._microscope.getChannel(channel).getLEDSetting(led).getIntensity(),
                lambda c, v: self._microscope.getChannel(channel).getLEDSetting(led).setIntensity(round(v)),
                power,
                nCycles
            )

            for cycle in range(nCycles):
                plannedExecutionTime: datetime = start + timedelta(seconds=cycle * interval)
                enqueueInterpolator(plannedExecutionTime, interpolator, cycle)

        parser.defineSentence(
            "{start:start}{, }adjust..." +
            "{\n  }{repetition:repetition}" +
            "{\n  }the power of the {led:led} led of channel {channel:defined-channels} to {power:led-power}.",
            evaluateAdjustLEDPower)

        def evaluateAdjustExposureTime(e: ParsedNode):
            tim: time = e.evaluate("start")
            repetition: List[int] = e.evaluate("repetition")
            interval: int = repetition[0]
            duration: int = repetition[1]

            channel: str = e.evaluate("channel")
            exposureTime: int = e.evaluate("exposure-time")

            start: datetime = datetime.combine(date.today(), tim)
            if self._globalStart > tim:
                start = start + timedelta(days=1)

            nCycles: int = 1 if duration < interval else duration // interval + 1  # integer division

            interpolator: Interpolator = Interpolator(
                lambda: self._microscope.getChannel(channel).getExposureTime(),
                lambda c, v: self._microscope.getChannel(channel).setExposureTime(round(v)),
                exposureTime,
                nCycles
            )

            for cycle in range(nCycles):
                plannedExecutionTime: datetime = start + timedelta(seconds=cycle * interval)
                enqueueInterpolator(plannedExecutionTime, interpolator, cycle)

        parser.defineSentence(
            "{start:start}{, }adjust..." +
            "{\n  }{repetition:repetition}" +
            "{\n  }the exposure time of channel {channel:defined-channels} to {exposure-time:exposure-time}.",
            evaluateAdjustExposureTime)

        parser.defineType("temperature", "{temperature:float}\u00B0C", None, True)

        parser.defineType("co2-concentration", "{CO2 concentration:float}%", None, True)

        def evaluateAdjustCO2Concentration(e: ParsedNode):
            tim: time = e.evaluate("start")
            repetition: List[int] = e.evaluate("repetition")
            interval: int = repetition[0]
            duration: int = repetition[1]

            co2Concentration: float = e.evaluate("co2-concentration")

            start: datetime = datetime.combine(date.today(), tim)
            if self._globalStart > tim:
                start = start + timedelta(days=1)

            nCycles: int = 1 if duration < interval else duration // interval + 1  # integer division

            interpolator: Interpolator = Interpolator(
                lambda: self._microscope.getCO2Concentration(),
                lambda c, v: self._microscope.setCO2Concentration(v),
                co2Concentration,
                nCycles
            )

            for cycle in range(nCycles):
                plannedExecutionTime: datetime = start + timedelta(seconds=cycle * interval)
                enqueueInterpolator(plannedExecutionTime, interpolator, cycle)

        parser.defineSentence(
            "{start:start}{, }adjust..." +
            "{\n  }{repetition:repetition}" +
            "{\n  }the CO2 concentration to {co2-concentration:co2-concentration}.",
            evaluateAdjustCO2Concentration)

        def evaluateAdjustTemperature(e: ParsedNode):
            tim: time = e.evaluate("start")
            repetition: List[int] = e.evaluate("repetition")
            interval: int = repetition[0]
            duration: int = repetition[1]

            temperature: float = e.evaluate("temperature")

            start: datetime = datetime.combine(date.today(), tim)
            if self._globalStart > tim:
                start = start + timedelta(days=1)

            nCycles: int = 1 if duration < interval else duration // interval + 1  # integer division

            interpolator: Interpolator = Interpolator(
                lambda: self._microscope.getTemperature(),
                lambda c, v: self._microscope.setTemperature(v),
                temperature,
                nCycles
            )

            for cycle in range(nCycles):
                plannedExecutionTime: datetime = start + timedelta(seconds=cycle * interval)
                enqueueInterpolator(plannedExecutionTime, interpolator, cycle)

        parser.defineSentence(
            "{start:start}{, }adjust..." +
            "{\n  }{repetition:repetition}" +
            "{\n  }the temperature to {temperature:temperature}.",
            evaluateAdjustTemperature)

        return parser
