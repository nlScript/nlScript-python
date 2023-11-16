from PyQt5.QtWidgets import QApplication

from nls.microscope.languagecontrol import LanguageControl
from nls.parser import Parser
from nls.ui.ui import ACEditor


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
