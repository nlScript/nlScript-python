import io
from datetime import datetime

from PySide2.QtWidgets import QApplication

from nlScript.microscope.languagecontrol import LanguageControl
from nlScript.microscope.microscope import Microscope, Position, Channel, LED, LEDSetting
from nlScript.parser import Parser
from nlScript.ui.ui import ACEditor


def main():
    lc: LanguageControl = LanguageControl()
    mic: Microscope = lc.microscope

    def onAcquire(position: Position, channel: Channel) -> None:
        current_date = datetime.now()
        timeStamp = current_date.strftime('%b %d, %Y, %H:%M:%S')

        output = io.StringIO()

        print(timeStamp, file=output)
        print("======================", file=output)
        print("Stage position: " + position.name, file=output)
        print("  - " + str(position.center), file=output)
        print("", file=output)
        print("Channel settings: " + channel.name, file=output)
        print("  - Exposure time: " + str(channel.getExposureTime()) + "ms", file=output)
        for led in LED:
            ledSetting: LEDSetting = channel.getLEDSetting(led)
            if ledSetting is not None:
                print("  - LED " + str(led.WAVELENGTH) + ": " + str(ledSetting.getIntensity()) + "%", file=output)
        print("", file=output)
        print("Optics:", file=output)
        print("  - Lens: " + str(mic.lens), file=output)
        print("  - Mag.Changer: " + str(mic.magnificationChanger), file=output)
        print("  - Binning: " + str(mic.binning), file=output)
        print("", file=output)
        print("Incubation:", file=output)
        print("  - Temperature: " + str(mic.getTemperature()) + "C", file=output)
        print("  - CO2 concentration: " + str(mic.getCO2Concentration()) + "%", file=output)
        print("", file=output)
        print("Acquire stack", file=output)
        print("", file=output)
        print("", file=output)
        contents = output.getvalue()
        output.close()
        text = editor.getOutputArea().document().toPlainText() + contents
        editor.getOutputArea().document().setPlainText(text)

    mic.setOnAcquire(onAcquire)

    parser: Parser = lc.initParser()
    parser.compile()
    app = QApplication([])
    editor: ACEditor = ACEditor(parser)
    editor.setBeforeRun(lambda: lc.reset())
    editor.setAfterRun(lambda: lc.getTimeline().process(lambda e: e()))
    editor.show()
    exit(app.exec_())


if __name__ == '__main__':
    main()
