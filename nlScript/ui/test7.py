import sys

from PyQt5.QtGui import QTextCursor, QColor
from PyQt5.QtWidgets import QTextEdit, QApplication, QWidget, QVBoxLayout, QPlainTextEdit


class TextEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(800, 600)
        self.setPlainText("bla bla bla")
        cursor = self.textCursor()
        fmt = cursor.charFormat()
        fmt.setBackground(QColor(255, 100, 100))

        # cursor.setPosition(0)
        # cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, 2)
        # cursor.setCharFormat(fmt)

        cursor.setPosition(4)
        cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, 2)
        cursor.setCharFormat(fmt)
        # cursor.clearSelection()

        cursor2 = self.textCursor()
        cursor2.setPosition(0)
        cursor2.insertText("hehe ")

        print(cursor.anchor())
        print(cursor.position())


        # self.setTextCursor(cursor)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    te = TextEditor()
    te.show()
    sys.exit(app.exec_())
