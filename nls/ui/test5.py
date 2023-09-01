import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor, QColor
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget, QRubberBand, QTextEdit

db = ((5,8,'A'),(20,35,'B'),(45,60,'C')) # start, end, and identifier of highlights

class TextEditor(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        text="This is example text that is several lines\nlong and also\nstrangely broken up and can be\nwrapped."
        self.setText(text)
        cursor = self.textCursor()
        for n in range(0,len(db)):
            row = db[n]
            startChar = row[0]
            endChar = row[1]
            id = row[2]
            cursor.setPosition(startChar)
            cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, endChar-startChar)
            charfmt = cursor.charFormat()
            charfmt.setBackground(QColor(Qt.yellow))
            cursor.setCharFormat(charfmt)
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def getBoundingRect(self, start, end):
        cursor = self.textCursor()
        cursor.setPosition(end)
        last_rect = end_rect = self.cursorRect(cursor)
        cursor.setPosition(start)
        first_rect = start_rect = self.cursorRect(cursor)
        if start_rect.y() != end_rect.y():
            cursor.movePosition(QTextCursor.StartOfLine)
            first_rect = last_rect = self.cursorRect(cursor)
            while True:
                cursor.movePosition(QTextCursor.EndOfLine)
                rect = self.cursorRect(cursor)
                if rect.y() < end_rect.y() and rect.x() > last_rect.x():
                    last_rect = rect
                moved = cursor.movePosition(QTextCursor.NextCharacter)
                if not moved or rect.y() > end_rect.y():
                    break
            last_rect = last_rect.united(end_rect)
        return first_rect.united(last_rect)

class Window(QWidget):
    def __init__(self):
        super(Window, self).__init__()
        self.edit = TextEditor(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.edit)
        self.boxes = []

    def showBoxes(self):
        while self.boxes:
            self.boxes.pop().deleteLater()
        viewport = self.edit.viewport()
        for start, end, ident in db:
            rect = self.edit.getBoundingRect(start, end)
            box = QRubberBand(QRubberBand.Rectangle, viewport)
            box.setGeometry(rect)
            box.show()
            self.boxes.append(box)

    def resizeEvent(self, event):
        self.showBoxes()
        super().resizeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    window.setGeometry(800, 100, 350, 150)
    window.show()
    window.showBoxes()
    sys.exit(app.exec_())