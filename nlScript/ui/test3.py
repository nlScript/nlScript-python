from __future__ import annotations

import time
import typing
from typing import cast, List

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, QStringListModel, QRect, QObject, QEvent, QModelIndex, \
    QAbstractListModel
from PyQt5.QtGui import QTextCursor, QKeyEvent, QColor, QPalette, QTextDocument
from PyQt5.QtWidgets import QCompleter, QPlainTextEdit, QApplication, QTextEdit, QItemDelegate, QWidget, QLabel, \
    QStyleOptionViewItem

from nlScript.autocompleter import IfNothingYetEnteredAutocompleter, Autocompleter
from nlScript.core.autocompletion import Autocompletion
from nlScript.ebnf.ebnfparser import ParseStartListener
from nlScript.ebnf.parselistener import ParseListener
from nlScript.evaluator import Evaluator
from nlScript.parsednode import ParsedNode
from nlScript.parser import Parser


class AwesomeTextEdit(QPlainTextEdit):
    def __init__(self, parser: Parser, parent=None):
        super(AwesomeTextEdit, self).__init__(parent)
        font = QtGui.QFont()
        font.setFamily("Courier")
        font.setPointSize(10)
        self.setFont(font)
        self.setBaseSize(800, 600)

        palette = self.palette()
        palette.setColor(QPalette.Highlight, QColor(184, 207, 229))
        self.setPalette(palette)

        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.parameterizedCompletion: ParameterizedCompletionContext | None = None

        self.parser = parser
        self.completer = MyCompleter(parent)
        self.completer.setWidget(self)
        self.completer.insertText.connect(self.insertCompletion)
#         self.insertPlainText("""
# Define channel 'dapi':
#   excite with 50% at 385nm
#   use an exposure time of 50ms.
#
# Define a position 'pos1':
#   50 x 50 x 50 microns
#   centered at (5, 5, 5) microns.
#
# At the beginning, acquire...
#   every 5
# """)
        self.document().contentsChange.connect(self.documentChanged)
        # self.addHighlight(21, 23)

    def documentChanged(self, pos: int, charsRemoved: int, charsAdded: int) -> None:
        print("Added {} characters at position {}".format(charsAdded, pos))
        print("Deleted {} characters at position {}".format(charsRemoved, pos))
        if self.parameterizedCompletion is not None:
            self.parameterizedCompletion.printHighlights()
        else:
            print("parameterizedCompletion is None")

    def insertCompletion(self, completion: str) -> None:
        print("insertCompletion: " + completion)
        tc = self.textCursor()
        # extra = (len(completion) - len(self.completer.completionPrefix()))
        # tc.insertText(completion[-extra:])
        tc.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, len(self.completer.completionPrefix()))

        try:
            completion.index("${")  # throws ValueError if '${' does not exist in completion
            self.cancelParameterizedCompletion()
            self.parameterizedCompletion = ParameterizedCompletionContext(tc=self)
            self.parameterizedCompletion.parameterChanged.connect(self.parameterChanged)
            self.parameterizedCompletion.replaceSelection(completion)
        except ValueError:
            # self.cancelParameterizedCompletion()
            tc.removeSelectedText()
            tc.insertText(completion)
            self.completer.popup().hide()
            # self.setTextCursor(tc)
            self.autocomplete()

    def parameterChanged(self, pIdx: int, wasLast: bool) -> None:
        if wasLast or pIdx == -1:
            self.parameterizedCompletion = None
            print("parameterChanged(): autocomplete")
            self.autocomplete()
            return
        self.autocomplete(False)  # needed for showing the popup

    def cancelParameterizedCompletion(self):
        print("cancelParameterizedCompletion")
        if self.parameterizedCompletion is not None:
            self.parameterizedCompletion.cancel()
        self.parameterizedCompletion = None

    def focusInEvent(self, event):
        if self.completer:
            self.completer.setWidget(self)
        QPlainTextEdit.focusInEvent(self, event)

    # def addHighlight(self, p1: int, p2: int) -> Highlight:
    #     # h = Highlight(p1, p2, self.document())
    #     # print(h)
    #
    #     selection = QTextEdit.ExtraSelection()
    #     color = QColor(184, 207, 229)
    #     selection.format.setBackground(color)
    #
    #     cursor = self.textCursor()
    #     cursor.setPosition(p1)
    #     cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, p2 - p1 + 1)
    #     selection.cursor = cursor
    #
    #     selections = self.extraSelections()
    #     selections.append(selection)
    #     self.setExtraSelections(selections)
    #     # self.calculateRubberBand(selection)
    #     return selection

    def calculateRect(self, selection: QTextEdit.ExtraSelection) -> QRect:
        # rect = self.cursorRect(selection.cursor)  # this is a 1-pixel wide rectangle at the end of the selection
        # s = selection.cursor.selectedText()
        # # print(s)
        # width = self.fontMetrics().boundingRect(s).width()
        # rect.setLeft(rect.left() - width - 1)  # changes the left coordinate and adjusts width accordingly
        a = selection.cursor.anchor()
        p = selection.cursor.position()
        if p < a:
            tmp = a
            a = p
            p = tmp
        a = a + 1
        c = self.textCursor()
        c.setPosition(a)
        l = self.cursorRect(c)
        c.setPosition(p)
        r = self.cursorRect(c)
        l.setRight(r.right())
        return l

    # def removeHighlight(self, h: Highlight):
    #     cursor = self.textCursor()
    #     cursor.setPosition(h._pos1)
    #     cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, h._pos2 - h._pos1 + 1)
    #     charfmt = cursor.charFormat()
    #     charfmt.clearBackground()
    #     cursor.setCharFormat(charfmt)
    #     self.framed_handler.unframe(cursor)
    #     h.remove()

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        super().paintEvent(e)
        # print("painting")
        painter = QtGui.QPainter(self.viewport())
        painter.begin(self)
        painter.setPen(QtGui.QColor(Qt.gray))

        if self.parameterizedCompletion is None:
            print("parameterizedCompletion is None")

        for selection in self.extraSelections():
            rect = self.calculateRect(selection)
            painter.drawRect(rect)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return and self.completer.popup().isVisible():
            self.completer.insertText.emit(self.completer.getSelected())
            self.completer.setCompletionMode(QCompleter.PopupCompletion)
            return

        # print("Has selection? ", self.textCursor().hasSelection())
        if self.parameterizedCompletion is not None:
            if self.parameterizedCompletion.handleKeyPressed(self, event):
                return

        if self.completer.popup().isVisible() and event.key() == Qt.Key.Key_Tab:
            self.completer.popup().hide()
            return

        QPlainTextEdit.keyPressEvent(self, event)

        print("event text = " + event.text())
        if len(event.text()) == 0:
            print("Ignoring key event *" + event.text() + "*")
            return
        print("autocomplete in keyevent")
        self.autocomplete()

    def autocomplete(self, autoinsertSingleOption: bool = True):
        # print("cursor position = ", self.textCursor().position())
        cursor = self.textCursor()
        cursor.setPosition(cursor.anchor())
        cr = self.cursorRect(cursor)

        # if len(tc.selectedText()) > 0:
        #     self.completer.setCompletionPrefix(tc.selectedText())
        textToCursor = self.toPlainText()[0:self.textCursor().anchor()]
        autocompletions: List[Autocompletion] = []
        self.parser.parse(textToCursor, autocompletions)

        print("textToCursor = " + textToCursor)
        print("autocompletions = " + ",".join(map(str, autocompletions)))

        if len(autocompletions) == 1 and autoinsertSingleOption:
            self.completer.setCompletions(autocompletions)
            alreadyEntered = autocompletions[0].alreadyEnteredText
            self.completer.setCompletionPrefix(alreadyEntered)
            self.insertCompletion(autocompletions[0].completion)
        elif len(autocompletions) > 1:
            print(" len > 2")
            self.completer.setCompletions(autocompletions)
            alreadyEntered = autocompletions[0].alreadyEnteredText
            self.completer.setCompletionPrefix(alreadyEntered)

            # print("text to cursor = *", self.toPlainText()[0:self.textCursor().position()], "*")
            popup = self.completer.popup()
            popup.setCurrentIndex(self.completer.completionModel().index(0, 0))

            cr.setWidth(self.completer.popup().sizeHintForColumn(0)
                        + self.completer.popup().verticalScrollBar().sizeHint().width())
            # cr.setWidth(200)
            print(str(cr))
            self.completer.complete(cr)
        else:
            self.completer.popup().hide()


class MyDelegate(QItemDelegate):
    def __init__(self, parent=None):
        QItemDelegate.__init__(self, parent)

    def createEditor(self, parent: QWidget, option: 'QStyleOptionViewItem', index: QtCore.QModelIndex) -> QWidget:
        ret = QLabel(parent)
        ret.setTextFormat(Qt.RichText)
        return ret

    def setEditorData(self, editor: QWidget, index: QtCore.QModelIndex) -> None:
        label = cast(QLabel, editor)
        label.setText(index.model().data(index))  # TODO use HTML to make parameters bold, move printNice to here.
        label.setTextFormat(Qt.RichText)


class MyCompleter(QCompleter):
    insertText = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        # QCompleter.__init__(self, ["test", "test2", "test3", "foo", "bar"], parent)
        QCompleter.__init__(self, parent)
        # self.setModel(PopupModel([], self))
        self.setModel(QStringListModel())
        self.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.highlighted[QModelIndex].connect(self.selectionChanged)
        self._completions: List[Autocompletion] = []
        self.lastSelected = -1
        self.popup().setItemDelegate(MyDelegate(self))

    def setCompletions(self, completions: List[Autocompletion]) -> None:
        self._completions = completions

        def printNice(c: Autocompletion) -> str:
            ret = c.completion
            parsedParams = []
            ParameterizedCompletionContext.parseParameters(ret, parsedParams)
            if ret.startswith("\n"):
                ret = "<new line>"  # "<strong>new</strong> line"
            if ret == "":
                ret = "<empty>"
            return ret

        cast(QStringListModel, self.model()).setStringList(map(printNice, completions))
        self.popup().setItemDelegate(MyDelegate(self))
        # self.model().setCompletions(completions)

    def selectionChanged(self, idx: QModelIndex) -> None:
        print("selectionChanged: ", idx)
        self.lastSelected = idx.row()

    def getSelected(self) -> str or None:
        print("lastSelected = ", self.lastSelected)
        return None if self.lastSelected < 0 else self._completions[self.lastSelected].completion


class PopupModel(QAbstractListModel):
    def __init__(self, autocompletions: List[Autocompletion], parent):
        super().__init__(parent)
        self._autocompletions = autocompletions

    def setCompletions(self, completions: List[Autocompletion]) -> None:
        self.beginResetModel()
        self._autocompletions = completions
        self.endResetModel()

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        print("data(" + str(index.row()) + ")")
        completion = self._autocompletions[index.row()].completion
        if completion.startswith("\n"):
            completion = "<br>"
        print("  return ", completion)
        return completion

    def rowCount(self, parent: QModelIndex = ...) -> int:
        print("rowCount()")
        print("  return ", len(self._autocompletions))
        return len(self._autocompletions)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return super().flags(index) | Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable


class Highlight:
    def __init__(self, pos1: int, pos2: int, doc: QTextDocument):
        self._pos1 = pos1
        self._pos2 = pos2
        self._doc = doc
        doc.contentsChange.connect(self.documentChanged)
        # try:
        #     doc.highlights.append(self)
        # except AttributeError:
        #     doc.highlights = [self]

    # def remove(self):
    #     self._doc.highlights.remove(self)
    # TODO remove param

    def documentChanged(self, pos: int, charsRemoved: int, charsAdded: int) -> None:
        if charsRemoved > 0:
            d1 = pos
            d2 = pos + charsRemoved - 1
            if d1 > self._pos2:
                pass
            elif d1 < self._pos1 and d2 > self._pos2:
                print("remove highlight")
                # self.remove()
            else:
                nBeforeHighlight = max(0, self._pos1 - d1)
                nAfterHighlight  = max(0, d2 - self._pos2)
                nInsideHighlight = charsRemoved - nBeforeHighlight - nAfterHighlight
                self._pos1 -= nBeforeHighlight
                self._pos2 -= (nInsideHighlight + nBeforeHighlight)

        if charsAdded > 0:
            if pos < self._pos1:
                self._pos1 += charsAdded
                self._pos2 += charsAdded
            elif pos <= self._pos2 + 1:
                self._pos2 += charsAdded

    def __str__(self):
        return "h[" + str(self._pos1) + "; " + str(self._pos2) + "]"


class ParameterizedCompletionContext(QObject):
    parameterChanged = QtCore.pyqtSignal(int, bool)

    def __init__(self, tc: QPlainTextEdit):
        super().__init__(parent=tc)
        self._tc = tc
        self._parameters: List[Param] = []
        self._active = True

    def printHighlights(self):
        for p in self._parameters:
            print(str(p))

    def addHighlight(self, name: str, i0: int, i1: int) -> Param:
        selection = QTextEdit.ExtraSelection()
        # color = QColor(184, 207, 229)
        # selection.format.setBackground(color)

        cursor = self._tc.textCursor()
        cursor.setPosition(i0 - 1)
        cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, i1 - i0 + 1)
        print("selected text = ", cursor.selectedText())
        selection.cursor = cursor

        selections = self._tc.extraSelections()
        selections.append(selection)
        self._tc.setExtraSelections(selections)
        # self.calculateRubberBand(selection)

        param = Param(name, selection)
        return param

    # def calculateRubberBand(self, selection: QTextEdit.ExtraSelection) -> QRubberBand:
    #     rect = self.calculateRect(selection)
    #     rubber = QRubberBand(QRubberBand.Rectangle, self)
    #     rubber.setGeometry(rect)
    #     rubber.show()
    #     return rubber

    def insertCompletion(self, offset: int, autocompletion: str) -> None:
        parsedParams: List[ParsedParam] = []
        insertionString = ParameterizedCompletionContext.parseParameters(autocompletion, parsedParams)
        cursor = self._tc.textCursor()
        cursor.setPosition(offset)
        cursor.insertText(insertionString)
        self._parameters.clear()
        for pp in parsedParams:
            self._parameters.append(self.addHighlight(pp.name, offset + pp.i0, offset + pp.i1))
        atEnd = offset + len(insertionString)
        self._parameters.append(self.addHighlight("", atEnd, atEnd))

        self.cycle(0)
        # self._tc.installEventFilter(self)

    def replaceSelection(self, autocompletion: str) -> None:
        parsedParams: List[ParsedParam] = []
        insertionString = ParameterizedCompletionContext.parseParameters(autocompletion, parsedParams)
        cursor = self._tc.textCursor()
        cursor.removeSelectedText()
        offset = cursor.position()
        cursor.insertText(insertionString)
        self._parameters.clear()
        for pp in parsedParams:
            self._parameters.append(self.addHighlight(pp.name, offset + pp.i0, offset + pp.i1))
        atEnd = offset + len(insertionString)
        self._parameters.append(self.addHighlight("", atEnd, atEnd))

        self.cycle(0)
        # self._tc.installEventFilter(self)

    def getParametersSize(self):
        return len(self._parameters)

    def getPreviousParameterIndexForCursorPosition(self, pos: int) -> int:
        reverse_it = reversed(list(enumerate(self._parameters)))
        return next((i for i, param in reverse_it if pos > param.highlight.cursor.position()), -1)

    def getNextParameterIndexForCursorPosition(self, pos: int) -> int:
        return next((i for i, param in enumerate(self._parameters) if pos < param.highlight.cursor.anchor() + 1), -1)

    def next(self) -> None:
        caret = self._tc.textCursor().position()
        idx = self.getNextParameterIndexForCursorPosition(caret)
        self.cycle(idx)

    def previous(self) -> None:
        caret = self._tc.textCursor().position()
        idx = self.getPreviousParameterIndexForCursorPosition(caret)
        self.cycle(idx)

    def cycle(self, currentParameterIndex: int) -> None:
        if not self._active:
            return
        nParameters = len(self._parameters)
        if nParameters == 0:
            return

        if currentParameterIndex == -1:
            return

        hl = self._parameters[currentParameterIndex].highlight
        last = currentParameterIndex == nParameters - 1

        cursor = self._tc.textCursor()
        cursor.setPosition(hl.cursor.anchor() + 1)
        cursor.setPosition(hl.cursor.position(), QTextCursor.KeepAnchor)
        self._tc.setTextCursor(cursor)
        self.parameterChanged.emit(currentParameterIndex, last)

        if last:
            self.cancel()

    def cancel(self) -> None:
        if not self._active:
            return
        self._tc.setExtraSelections([])
        self.parameterChanged.disconnect()

    def handleKeyPressed(self, obj: QObject, event: QKeyEvent):
        if event.type() == QEvent.KeyPress and obj is self._tc:
            print("keyPressed")
            if not self._active:
                return False
            # if event.isAccepted():
            #     return False
            cursor = self._tc.textCursor().position()
            print("key = ", event.key())
            if event.key() == Qt.Key_Tab or event.key() == Qt.Key_Return:
                print("  pressed TAB")
                self.next()
                event.accept()
                return True
            elif event.key() == Qt.Key_Backtab:
                print("  pressed BACKTAB")
                self.previous()
                event.accept()
                return True
            elif event.key() == Qt.Key_Escape:
                self.cancel()
                event.accept()
                return True
        return False

    @staticmethod
    def parseParameters(paramString: str, ret: List[ParsedParam]) -> str:
        varName = None
        insertString = ""
        l = len(paramString)
        hlStart = -1
        i = 0
        while i < l:
            cha = paramString[i]
            if cha == '$' and i < l - 1 and paramString[i + 1] == '{':
                if varName is None:
                    varName = ""
                    hlStart = len(insertString)
                    i = i + 1
                else:
                    raise Exception("Expected '}' before next '${'")

            elif varName is not None and cha == '}':
                hlEnd = len(insertString)
                ret.append(ParsedParam(varName, hlStart, hlEnd))  # hlEnd is exclusive
                varName = None

            elif varName is not None:
                varName = varName + cha
                insertString = insertString + cha
            else:
                insertString = insertString + cha
            i = i + 1
        return insertString


class ParsedParam:
    def __init__(self, name: str, i0: int, i1: int):
        self._name = name
        self._i0 = i0
        self._i1 = i1

    @property
    def i0(self):
        return self._i0

    @property
    def i1(self):
        return self._i1

    @property
    def name(self):
        return self._name


class Param:
    def __init__(self, name: str, selection: QTextEdit.ExtraSelection):
        self._name = name
        self._highlight = selection

    @property
    def name(self):
        return self._name

    @property
    def highlight(self):
        return self._highlight

    def __str__(self):
        c = self._highlight.cursor
        return "{} : [{}, {}[".format(self._name, c.anchor(), c.position())


def initParser():
    parser = Parser()
    parser.defineType("color", "blue", None)
    parser.defineType("color", "green", None)
    parser.defineSentence("My favorite color is {color:color}.", None)
    return parser


def initParser2():
    definedChannels = []
    definedRegions  = []

    def clearChannelsAndRegions():
        definedChannels.clear()
        definedRegions.clear()

    parser = Parser()
    parser.addParseStartListener(ParseStartListener(clearChannelsAndRegions))

    parser.defineType("led", "385nm", None)
    parser.defineType("led", "470nm", None)
    parser.defineType("led", "567nm", None)
    parser.defineType("led", "625nm", None)

    parser.defineType("led-power", "{<led-power>:int}%", None, True)
    parser.defineType("exposure-time", "{<exposure-time>:int}ms", None, True)
    parser.defineType("led-setting", "{led-power:led-power} at {wavelength:led}", None, True)
    parser.defineType("another-led-setting", ", {led-setting:led-setting}", None, True)

    parser.defineType("channel-name", "'{<name>:[A-Za-z0-9]:+}'", None, IfNothingYetEnteredAutocompleter("'${name}'"))

    parser.defineSentence(
            "Define channel {channel-name:channel-name}:" +
            "{\n  }excite with {led-setting:led-setting}{another-led-setting:another-led-setting:0-3}" +
            "{\n  }use an exposure time of {exposure-time:exposure-time}.",
            None
    ).onSuccessfulParsed(ParseListener(lambda n: definedChannels.append(n.getParsedString("channel-name"))))

    # Define "Tile Scan 1" as a (w x h x d) region centered at (x, y, z)
    parser.defineType("region-name", "'{<region-name>:[a-zA-Z0-9]:+}'", None, IfNothingYetEnteredAutocompleter("'${region-name}'"))
    parser.defineType("region-dimensions", "{<width>:float} x {<height>:float} x {<depth>:float} microns", None, True)
    parser.defineType("region-center", "{<center>:tuple<float,x,y,z>} microns", None, True)
    parser.defineType("sentence",
            "Define a position {region-name:region-name}:" +
                    "{\n  }{region-dimensions:region-dimensions}" +
                    "{\n  }centered at {region-center:region-center}.",
            None
    ).onSuccessfulParsed(ParseListener(lambda n: definedRegions.append(n.getParsedString("region-name"))))

    parser.defineSentence("Define the output folder at {folder:path}.", None)

    parser.defineType("defined-channels", "'{channel:[A-Za-z0-9]:+}'",
            evaluator=None,
            autocompleter=Autocompleter(lambda e: ";;;".join(definedChannels)))

    parser.defineType("defined-positions", "'{position:[A-Za-z0-9]:+}'",
            evaluator=Evaluator(lambda e: e.getParsedString("position")),
            autocompleter=Autocompleter(lambda e: ";;;".join(definedRegions)))

    parser.defineType("time-unit", "second(s)", evaluator=Evaluator(lambda: 1))
    parser.defineType("time-unit", "minute(s)", evaluator=Evaluator(lambda: 60))
    parser.defineType("time-unit", "hour(s)",   evaluator=Evaluator(lambda: 3600))

    def inSeconds(e: ParsedNode):
        n = float(e.evaluate("n"))
        unit = int(e.evaluate("time-unit"))
        return round(n * unit)
    parser.defineType("time-interval", "{n:float} {time-unit:time-unit}", Evaluator(inSeconds), True)

    parser.defineType("z-distance", "{z-distance:float} microns", None, True)

    parser.defineType("lens",  "5x lens", None)
    parser.defineType("lens", "20x lens", None)

    parser.defineType("mag", "0.5x magnification changer", None)
    parser.defineType("mag", "1.0x magnification changer", None)
    parser.defineType("mag", "2.0x magnification changer", None)

    parser.defineType("binning", "1 x 1", evaluator=Evaluator(lambda: 1))
    parser.defineType("binning", "2 x 2", evaluator=Evaluator(lambda: 2))
    parser.defineType("binning", "4 x 4", evaluator=Evaluator(lambda: 4))
    parser.defineType("binning", "8 x 8", evaluator=Evaluator(lambda: 8))

    parser.defineType("temperature", "{temperature:float}\u00B0C", None, True)
    parser.defineType("co2-concentration", "{CO2 concentration:float}%", None, True)

    parser.defineType("incubation", "set the temperature to {temperature:temperature}", None)

    parser.defineType("incubation", "set the CO2 concentration to {co2-concentration:co2-concentration}", None)

    parser.defineType("acquisition",
            "acquire..." +
                    "{\n  }every {interval:time-interval} for {duration:time-interval}" +
                    "{\n  }position(s) {positions:list<defined-positions>}" +
                    "{\n  }channel(s) {channels:list<defined-channels>}" +
                    # "{\n  }with a resolution of {dx:float} x {dy:float} x {dz:float} microns.",
                    "{\n  }with a plane distance of {dz:z-distance}" +
                    "{\n  }using the {lens:lens} with the {magnification:mag} and a binning of {binning:binning}",
            None)

    parser.defineType("start", "At the beginning",            None)
    parser.defineType("start", "At {time:time}",              None, True)
    parser.defineType("start", "After {delay:time-interval}", None, True)

    parser.defineSentence("{start:start}, {acquisition:acquisition}.", None)

    parser.defineSentence("{start:start}, {incubation:incubation}.", None)
    return parser


def test():
    parser = initParser2()
    parser.compile()
    textToCursor = "Define channel 'DAPI':\n  excite with "
    autocompletions: List[Autocompletion] = []
    parser.parse(textToCursor, autocompletions)
    print("autocompletions: ", ",".join(map(str, autocompletions)))


def testPathAutocompletion():
    parser = initParser2()
    parser.compile()
    # textToCursor = "Define the output folder at 'D"
    # textToCursor = "Define the output folder at 'D:\\"
    textToCursor = "Define the output folder at 'D:\\3Dscript.server_Data\\"
    autocompletions: List[Autocompletion] = []
    parser.parse(textToCursor, autocompletions)
    print("autocompletions: ", ",".join(map(str, autocompletions)))


def doProfile():
    parser = initParser2()
    parser.compile()

    textToCursor = "Define channel 'DAPI':\n  excite with 5% at 470nm"
    autocompletions: List[Autocompletion] = []

    print("start")
    start = time.time()
    import cProfile, pstats, io
    from pstats import SortKey
    pr = cProfile.Profile()
    pr.enable()

    parser.parse(textToCursor, autocompletions)
    # parser.parse(textToCursor, None)

    pr.disable()
    s = io.StringIO()
    sortby = SortKey.TIME
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    print(s.getvalue())
    end = time.time()

    print("Needed ", (end - start))

    import nlScript.autocompleter
    print("EntireSequenceAutocompleter called", nlScript.autocompleter.EntireSequenceAutocompleter.calledNTimes)

    print(",".join(map(lambda c: c.completion, autocompletions)))


if __name__ == "__main__":
    # doProfile()
    # testPathAutocompletion()
    # if True:
    #     exit(0)

    parser = initParser2()
    parser.compile()

    app = QApplication([])
    te = AwesomeTextEdit(parser)
    te.show()
    exit(app.exec_())
