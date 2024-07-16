from PySide2.QtWidgets import QApplication

from nlScript.microscope.languagecontrol import LanguageControl
from nlScript.parser import Parser
from nlScript.ui.ui import ACEditor


def main():
    lc: LanguageControl = LanguageControl()
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
