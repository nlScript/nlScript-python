import sys

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtGui import QTextCursor, QColor, QPalette
from PyQt5.QtWidgets import QWidget, QPlainTextEdit, QPushButton, QGridLayout, QTextEdit, QApplication


class Template(QWidget):

    def __init__(self):
        super().__init__()
        self.textbox = QTextEdit()
        font = QtGui.QFont()
        font.setFamily("Courier")
        font.setPointSize(10)
        self.textbox.setFont(font)

        palette = self.textbox.palette()
        palette.setColor(QPalette.Highlight, QColor(184, 207, 229))
        self.textbox.setPalette(palette)

        self.textbox.insertPlainText("bla bla bla")
        btn = QPushButton('Highlight')
        btn.clicked.connect(self.highlight_word)
        btn2 = QPushButton('Get Selection')
        btn2.clicked.connect(self.get_selections)
        grid = QGridLayout(self)
        grid.addWidget(btn, 0, 0)
        grid.addWidget(btn2, 0, 1)
        grid.addWidget(self.textbox, 1, 0, 1, 2)

        c = self.textbox.textCursor()
        c.setPosition(0)
        c.setPosition(3, QTextCursor.KeepAnchor)
        self.textbox.setTextCursor(c)
        # self.highlight_word()
        self.textbox.setFocus()

        self.textbox.installEventFilter(self)

    def eventFilter(self, a0: QObject, a1: QEvent) -> bool:
        c = self.textbox.textCursor()
        print("has selection? ", c.hasSelection())
        return False

    def highlight_word(self):
        selection = QTextEdit.ExtraSelection()
        selection.cursor.joinPreviousEditBlock()
        color = QColor(184, 207, 229)
        selection.format.setBackground(color)

        cursor = self.textbox.textCursor()
        cursor.setPosition(-1)
        cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, 3)
        selection.cursor = cursor

        selections = self.textbox.extraSelections()
        selections.append(selection)
        self.textbox.setExtraSelections(selections)
        print(selection.format.background().color().getRgb())

        # c = self.textbox.textCursor()
        # c.setPosition(3)
        # # c.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, 6)
        # c.setPosition(6, QTextCursor.KeepAnchor)
        # format = c.charFormat()
        # format.setBackground(QColor(Qt.yellow))
        # c.setCharFormat(format)
        # # c.select(QTextCursor.WordUnderCursor)
        # self.textbox.setTextCursor(c)

    def get_selections(self):
        for selection in self.textbox.extraSelections():
            print(selection.cursor.selectedText(),
                  selection.format.background().color().getRgb(),
                  selection.cursor.anchor(),
                  selection.cursor.position())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = Template()
    gui.show()
    sys.exit(app.exec_())