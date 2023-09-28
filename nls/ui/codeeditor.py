from typing import List

from PyQt5 import QtGui
from PyQt5.QtCore import QSize, QRect, Qt
from PyQt5.QtGui import QPaintEvent, QColor, QTextFormat, QPainter, QTextBlock, QTextCursor, QTextCharFormat
from PyQt5.QtWidgets import QPlainTextEdit, QWidget, QTextEdit


# https://doc.qt.io/qt-6.2/qtwidgets-widgets-codeeditor-example.html
class CodeEditor(QPlainTextEdit):

    lineNumberForeground = QColor(108, 108, 108)
    lineNumberBackground = QColor(245, 245, 245)
    lineNumberPadding = 10
    lineNumberBorderColor = QColor(221, 221, 221)
    activeLineBackground = QColor(255, 251, 0, 67)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        font = self.font()
        font.setBold(True)
        self.document().setDefaultFont(font)
        self.lineNumberArea = LineNumberArea(self)
        self.currentLineSelection: QTextEdit.ExtraSelection | None = None
        self.myExtraSelections: List[QTextEdit.ExtraSelection] = []

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

    def removeExtraSelection(self, s: QTextEdit.ExtraSelection) -> None:
        if s is not None:
            try:
                self.myExtraSelections.remove(s)
            except ValueError:
                print("no existing ExtraSelection " + str(s))

    def addExtrasSelection(self, s: QTextEdit.ExtraSelection) -> None:
        self.myExtraSelections.append(s)

    def prependExtraSelection(self, s: QTextEdit.ExtraSelection) -> None:
        self.myExtraSelections.insert(0, s)

    def updateExtraSelections(self):
        self.setExtraSelections(self.myExtraSelections)


    def lineNumberAreaPaintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), CodeEditor.lineNumberBackground)
        painter.setPen(CodeEditor.lineNumberBorderColor)
        xpos = event.rect().left() + self.lineNumberAreaWidth() - 1
        painter.drawLine(xpos, event.rect().top(), xpos, event.rect().bottom())

        block: QTextBlock = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(CodeEditor.lineNumberForeground)
                painter.drawText(0, top, self.lineNumberArea.width() - CodeEditor.lineNumberPadding, self.fontMetrics().height(), Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            blockNumber = blockNumber + 1

    def lineNumberAreaWidth(self) -> int:
        digits: int = 1
        maxV: int = max(1, self.blockCount())
        while maxV >= 10:
            maxV = maxV // 10
            digits = digits + 1

        if digits < 3:
            digits = 3

        space: int = 2 * CodeEditor.lineNumberPadding + self.fontMetrics().horizontalAdvance("9") * digits
        return space

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        super().resizeEvent(e)
        cr: QRect = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def updateLineNumberAreaWidth(self, newBlockCount: int) -> None:
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def highlightCurrentLine(self) -> None:
        self.removeExtraSelection(self.currentLineSelection)

        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(CodeEditor.activeLineBackground)
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        tc = self.textCursor()
        tc.setPosition(tc.position(), QTextCursor.MoveAnchor)
        selection.cursor = tc
        self.currentLineSelection = selection

        self.prependExtraSelection(selection)
        print("selections", len(self.myExtraSelections))
        self.updateExtraSelections()

    def updateLineNumberArea(self, rect: QRect, dy: int) -> None:
        if dy > 0:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)


class LineNumberArea(QWidget):
    def __init__(self, editor: CodeEditor):
        super().__init__(editor)
        self._codeEditor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self._codeEditor.lineNumberAreaPaintEvent(event)