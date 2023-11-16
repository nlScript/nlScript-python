from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List


class LED(Enum):
    LED_385 = 385
    LED_470 = 470
    LED_567 = 567
    LED_625 = 625

    def __init__(self, wl):
        self.WAVELENGTH = wl


class LEDSetting:
    def __init__(self, led: LED, intensity: int):
        self._led = led
        self._intensity = intensity

    @property
    def led(self) -> LED:
        return self._led

    def setIntensity(self, intensity: int) -> None:
        self._intensity = intensity

    def getIntensity(self) -> int:
        return self._intensity


class Channel:
    def __init__(self, name: str, first: LEDSetting, remaining: List[LEDSetting], exposureTime: int):
        self._name = name
        self._ledSettings = [first] + remaining
        self._exposureTime = exposureTime

    @property
    def name(self) -> str:
        return self._name

    def getLEDSetting(self, led: LED) -> LEDSetting or None:
        for ledSetting in self._ledSettings:
            if ledSetting.led == led:
                return ledSetting
        return None

    def getExposureTime(self) -> int:
        return self._exposureTime

    def setExposureTime(self, exposureTime: int) -> None:
        self._exposureTime = exposureTime


class Lens(Enum):
    FIVE = (5, "5x")
    TWENTY = (20, "20x")

    def __init__(self, magnification: float, label: str):
        self.magnification = magnification
        self.label = label

    def __str__(self) -> str:
        return self.label


class MagnificationChanger(Enum):
    ZERO_FIVE = (0.5, "0.5x")
    ONE_ZERO = (1.0, "1.0x")
    TWO_ZERO = (2.0, "2.0x")

    def __init__(self, magnification: float, label: str):
        self.magnification = magnification
        self.label = label

    def __str__(self) -> str:
        return self.label


class Binning(Enum):
    ONE = (1, "1x1")
    TWO = (2, "2x2")
    THREE = (3, "3x3")
    FOUR = (4, "4x4")
    FIVE = (5, "5x5")

    def __init__(self, binning: int, label: str):
        self.binning = binning
        self.label = label

    def __str__(self) -> str:
        return self.label


class Tuple3D:
    def __init__(self, t: List[float]):
        self._x = t[0]
        self._y = t[1]
        self._z = t[2]

    @property
    def x(self) -> float:
        return self._x

    @property
    def y(self) -> float:
        return self._y

    @property
    def z(self) -> float:
        return self._z

    def __str__(self) -> str:
        return f"({self._x}, {self._y}, {self._z})"


class Position:
    def __init__(self, name, center, extent):
        self._name = name
        self._center = Tuple3D(center)
        self._extent = Tuple3D(extent)

    @property
    def name(self) -> str:
        return self._name

    @property
    def center(self) -> Tuple3D:
        return self._center

    @property
    def extent(self) -> Tuple3D:
        return self._extent

    def __str__(self):
        return self._name + str(self._center)


class Incubation:
    def __init__(self):
        self._temperature = 20
        self._co2Concentration = 0

    @property
    def temperature(self) -> float:
        return self._temperature

    @property
    def co2Concentration(self) -> float:
        return self._co2Concentration

    def setTemperature(self, temperature: float) -> None:
        self._temperature = temperature

    def setCO2Concentration(self, co2_concentration: float) -> None:
        self._co2Concentration = co2_concentration

    def reset(self) -> None:
        self._temperature = 20
        self._co2Concentration = 0


class Microscope:

    ALL_CHANNELS = "ALL_CHANNELS"
    ALL_POSITIONS = "ALL_POSITIONS"

    def __init__(self):
        self._channels = []
        self._positions = []
        self._lens = Lens.FIVE
        self._magnificationChanger = MagnificationChanger.ONE_ZERO
        self._binning = Binning.ONE
        self._incubation = Incubation()

    def reset(self):
        self._channels.clear()
        self._positions.clear()
        self._lens = Lens.FIVE
        self._magnificationChanger = MagnificationChanger.ONE_ZERO
        self._binning = Binning.ONE
        self._incubation.reset()

    def addChannel(self, channel: Channel) -> None:
        self._channels.append(channel)

    def getChannel(self, name: str) -> Channel or None:
        for channel in self._channels:
            if channel.name == name:
                return channel
        return None

    def clearChannels(self) -> None:
        self._channels.clear()

    def addPosition(self, position: Position) -> None:
        self._positions.append(position)

    def getPosition(self, name: str) -> Position or None:
        for position in self._positions:
            if position.name == name:
                return position
        return None

    def clearPositions(self) -> None:
        self._positions.clear()

    def getTemperature(self) -> float:
        return self._incubation.temperature

    def setTemperature(self, temperature: float) -> None:
        self._incubation.setTemperature(temperature)

    def getCO2Concentration(self) -> float:
        return self._incubation.co2Concentration

    def setCO2Concentration(self, co2_concentration: float) -> None:
        self._incubation.setCO2Concentration(co2_concentration)

    def getLens(self) -> Lens:
        return self._lens

    def setLens(self, lens: Lens) -> None:
        self._lens = lens

    def getMagnificationChanger(self) -> MagnificationChanger:
        return self._magnificationChanger

    def setMagnificationChanger(self, mag: MagnificationChanger) -> None:
        self._magnificationChanger = mag

    def setBinning(self, binning: Binning) -> None:
        self._binning = binning

    def acquire(self, positionNames: List[str], channelNames: List[str], dz: float) -> None:
        if len(channelNames) > 0 and channelNames[0] == Microscope.ALL_CHANNELS:
            channels: List[Channel] = self._channels
        else:
            channels: List[Channel] = [self.getChannel(channelName) for channelName in channelNames]

        if len(positionNames) > 0 and positionNames[0] == Microscope.ALL_POSITIONS:
            positions = self._positions
        else:
            positions = [self.getPosition(positionName) for positionName in positionNames]

        self.acquirePositionsAndChannels(positions, channels, dz)

    def acquirePositionsAndChannels(self, positions: List[Position], channels: List[Channel], _dz: float) -> None:
        for position in positions:
            for channel in channels:
                self.acquireSinglePositionAndChannel(position, channel)

    def acquireSinglePositionAndChannel(self, position: Position, channel: Channel):
        current_date = datetime.now()
        timeStamp = current_date.strftime('%b %d, %Y, %H:%M:%S')

        print(timeStamp)
        print("======================")
        print("Stage position: " + position.name)
        print("  - " + str(position.center))
        print()
        print("Channel settings: " + channel.name)
        print("  - Exposure time: " + str(channel.getExposureTime()) + "ms")
        for led in LED:
            ledSetting: LEDSetting = channel.getLEDSetting(led)
            if ledSetting is not None:
                print("  - LED " + str(led.WAVELENGTH) + ": " + str(ledSetting.getIntensity()) + "%")
        print()
        print("Optics:")
        print("  - Lens: " + str(self._lens))
        print("  - Mag.Changer: " + str(self._magnificationChanger))
        print("  - Binning: " + str(self._binning))
        print()
        print("Incubation:")
        print("  - Temperature: " + str(self.getTemperature()) + "C")
        print("  - CO2 concentration: " + str(self.getCO2Concentration()) + "%")
        print()
        print("Acquire stack")
        print()
        print()
