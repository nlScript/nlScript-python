from __future__ import annotations

import time
from typing import cast, List

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, QStringListModel, QRect, QObject, QEvent, QModelIndex
from PyQt5.QtGui import QTextCursor, QKeyEvent, QColor, QPalette, QFont
from PyQt5.QtWidgets import QCompleter, QPlainTextEdit, QApplication, QTextEdit, QItemDelegate, QStyleOptionViewItem, \
    QWidget, QSplitter, QPushButton, QVBoxLayout

from nls.autocompleter import IfNothingYetEnteredAutocompleter, Autocompleter
from nls.core.autocompletion import Autocompletion
from nls.core.matcher import Matcher
from nls.ebnf.ebnfparser import ParseStartListener
from nls.ebnf.parselistener import ParseListener
from nls.evaluator import Evaluator
from nls.parsednode import ParsedNode
from nls.parseexception import ParseException
from nls.parser import Parser
from nls.ui.codeeditor import CodeEditor


class ACEditor(QWidget):
    def __init__(self, parser: Parser, parent=None):
        super(ACEditor, self).__init__(parent)

        self._parser = parser

        vbox = QVBoxLayout(self)

        splitter = QSplitter(Qt.Vertical)

        self._textEdit = AutocompletionContext(parser, parent=splitter)
        self._outputArea = QPlainTextEdit(parent=splitter)
        font = QtGui.QFont()
        font.setFamily("Courier")
        font.setPointSize(10)
        font.setBold(True)
        self._outputArea.setFont(font)
        self._outputArea.setReadOnly(True)

        splitter.addWidget(self._textEdit)
        splitter.addWidget(self._outputArea)
        splitter.setSizes([480, 120])

        vbox.addWidget(splitter)

        run = QPushButton("Run", self)
        run.clicked.connect(self.run)
        vbox.addWidget(run, alignment=Qt.AlignCenter)

        self.setLayout(vbox)
        self.resize(800, 600)

    def getText(self) -> str:
        return self._textEdit.document().toPlainText()

    def run(self) -> None:
        try:
            self._outputArea.setPlainText("")
            print("Parsing...")
            pn: ParsedNode = self._parser.parse(self.getText())
            print("Evaluating...")
            pn.evaluate()
            print("Done")
        except ParseException as e:
            self._outputArea.setPlainText(e.getError())
            pass


class ErrorHighlight:
    def __init__(self, tc: CodeEditor):
        self._tc = tc
        self.highlight: QTextEdit.ExtraSelection | None = None

    def setError(self, i0: int, i1: int) -> None:
        self.clearError()
        self.highlight = QTextEdit.ExtraSelection()

        cursor = self._tc.textCursor()
        cursor.setPosition(i0)
        cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, i1 - i0)
        self.highlight.format.setForeground(QColor(255, 100, 100))
        self.highlight.format.setFontWeight(QFont.Bold)
        self.highlight.cursor = cursor

        self._tc.addExtrasSelection(self.highlight)
        self._tc.updateExtraSelections()

    def clearError(self) -> None:
        if self.highlight is not None:
            self._tc.removeExtraSelection(self.highlight)


class AutocompletionContext(CodeEditor):
    def __init__(self, parser:Parser, parent=None):
        super(AutocompletionContext, self).__init__(parent)

        self._errorHighlight = ErrorHighlight(tc=self)

        font = QtGui.QFont()
        font.setFamily("Courier")
        font.setPointSize(10)
        font.setBold(True)
        self.setFont(font)
        self.setBaseSize(800, 600)

        palette = self.palette()
        palette.setColor(QPalette.Highlight, QColor(184, 207, 229))
        self.setPalette(palette)

        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.parameterizedCompletion: ParameterizedCompletionContext | None = None

        self.parser = parser
        self.completer = ACPopup(parent)
        self.completer.setWidget(self)

    def insertCompletion(self, completion: str) -> None:
        tc = self.textCursor()
        # select the previous len(completionPrefix) characters:
        tc.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, len(self.completer.completionPrefix()))

        try:
            completion.index("${")  # throws ValueError if '${' does not exist in completion
            self.cancelParameterizedCompletion()
            self.parameterizedCompletion = ParameterizedCompletionContext(tc=self)
            self.parameterizedCompletion.parameterChanged.connect(self.parameterChanged)
            self.parameterizedCompletion.replaceSelection(completion)
        except ValueError:
            self.cancelParameterizedCompletion()
            tc.removeSelectedText()
            tc.insertText(completion)
            self.completer.popup().hide()
            self.autocomplete()

    def parameterChanged(self, pIdx: int, wasLast: bool) -> None:
        if wasLast:
            self.cancelParameterizedCompletion()
            self.autocomplete()
            return

        # parameter changed, and there are multiple autocompletion options: => show popup
        # but don't automatically insert
        self.autocomplete(False)

    def cancelParameterizedCompletion(self):
        if self.parameterizedCompletion is not None:
            self.parameterizedCompletion.cancel()
        self.parameterizedCompletion = None

    def focusInEvent(self, event):
        if self.completer:
            self.completer.setWidget(self)
        QPlainTextEdit.focusInEvent(self, event)

    def calculateRect(self, selection: QTextEdit.ExtraSelection) -> QRect:
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

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        super().paintEvent(e)
        if self.parameterizedCompletion is None:
            return
        painter = QtGui.QPainter(self.viewport())
        painter.begin(self)
        painter.setPen(QtGui.QColor(Qt.gray))

        for p in self.parameterizedCompletion.parameters:
            selection = p.highlight
            rect = self.calculateRect(selection)
            rect = QRect(rect)
            painter.drawRect(rect)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return and self.completer.popup().isVisible():
            self.insertCompletion(self.completer.getSelected())
            self.completer.setCompletionMode(QCompleter.PopupCompletion)
            return

        if self.parameterizedCompletion is not None:
            if self.parameterizedCompletion.handleKeyPressed(self, event):
                return

        if self.completer.popup().isVisible() and event.key() == Qt.Key.Key_Tab:
            self.completer.popup().hide()
            return

        QPlainTextEdit.keyPressEvent(self, event)

        if len(event.text()) != 0:
            self.autocomplete()

    def autocomplete(self, autoinsertSingleOption: bool = True):
        cursor = self.textCursor()
        cursor.setPosition(cursor.anchor())
        cr = self.cursorRect(cursor)

        entireText = self.toPlainText()
        anchor = self.textCursor().anchor()
        cursorIsAtEnd = anchor == len(entireText) or len(entireText[anchor:].strip()) == 0
        autoinsertSingleOption = autoinsertSingleOption and cursorIsAtEnd

        textToCursor = self.toPlainText()[0:anchor]
        autocompletions: List[Autocompletion] = []

        self._errorHighlight.clearError()
        try:
            self.parser.parse(textToCursor, autocompletions)
        except ParseException as e:
            f: Matcher = e.getFirstAutocompletingAncestorThatFailed().matcher
            self._errorHighlight.setError(f.pos, f.pos + len(f.parsed))
            return

        if len(autocompletions) == 1 and autoinsertSingleOption:
            self.completer.setCompletions(autocompletions)
            alreadyEntered = autocompletions[0].alreadyEnteredText
            self.completer.setCompletionPrefix(alreadyEntered)
            self.insertCompletion(autocompletions[0].completion)
        elif len(autocompletions) > 1:
            self.completer.setCompletions(autocompletions)
            alreadyEntered = autocompletions[0].alreadyEnteredText
            self.completer.setCompletionPrefix(alreadyEntered)

            remainingText = entireText[anchor:]
            matchingLength = 0
            for ac in autocompletions:
                remainingCompletion = ac.completion[len(alreadyEntered):]
                if remainingText.startswith(remainingCompletion):
                    matchingLength = len(remainingCompletion)
                    break

            if matchingLength > 0:
                cursor = self.textCursor()
                cursor.setPosition(anchor)
                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, matchingLength)
                self.setTextCursor(cursor)

            popup = self.completer.popup()
            popup.setCurrentIndex(self.completer.completionModel().index(0, 0))

            cr.moveLeft(cr.left() + self.viewportMargins().left())
            cr.setWidth(self.completer.popup().sizeHintForColumn(0)
                        + self.completer.popup().verticalScrollBar().sizeHint().width())
            self.completer.complete(cr)
        else:
            self.completer.popup().hide()


class MyDelegate(QItemDelegate):
    def __init__(self, parent=None):
        QItemDelegate.__init__(self, parent)

    def paint(self, painter: QtGui.QPainter, option: 'QStyleOptionViewItem', index: QtCore.QModelIndex) -> None:
        QItemDelegate.paint(self, painter, option, index)
        # text = index.model().data(index)
        # parsedParams = []
        # ParameterizedCompletionContext.parseParameters(text, parsedParams)
        # self.drawDisplay(painter, option, option.rect, text)


class ACPopup(QCompleter):

    def __init__(self, parent=None):
        QCompleter.__init__(self, parent)
        self.setModel(QStringListModel())
        self.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.highlighted[QModelIndex].connect(self.selectionChanged)
        self._completions: List[Autocompletion] = []
        self.lastSelected = -1
        # self.popup().setItemDelegate(MyDelegate(self))

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

    def selectionChanged(self, idx: QModelIndex) -> None:
        self.lastSelected = idx.row()

    def getSelected(self) -> str or None:
        return None if self.lastSelected < 0 else self._completions[self.lastSelected].completion


class ParameterizedCompletionContext(QObject):
    parameterChanged = QtCore.pyqtSignal(int, bool)

    def __init__(self, tc: CodeEditor):
        super().__init__(parent=tc)
        self._tc = tc
        self._parameters: List[Param] = []

    @property
    def parameters(self) -> List[Param]:
        return self._parameters

    def printHighlights(self):
        for p in self._parameters:
            print(str(p))

    def addHighlight(self, name: str, i0: int, i1: int) -> Param:
        selection = QTextEdit.ExtraSelection()

        cursor = self._tc.textCursor()
        cursor.setPosition(i0 - 1)
        cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, i1 - i0 + 1)
        selection.cursor = cursor

        self._tc.addExtrasSelection(selection)
        self._tc.updateExtraSelections()

        param = Param(name, selection)
        return param

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

    def replaceSelection(self, autocompletion: str) -> None:
        parsedParams: List[ParsedParam] = []
        insertionString = ParameterizedCompletionContext.parseParameters(autocompletion, parsedParams)
        cursor = self._tc.textCursor()
        cursor.removeSelectedText()
        offset = cursor.position()
        cursor.insertText(insertionString)
        for p in self._parameters:
            self._tc.removeExtraSelection(p.highlight)
        self._tc.updateExtraSelections()
        self._parameters.clear()
        for pp in parsedParams:
            self._parameters.append(self.addHighlight(pp.name, offset + pp.i0, offset + pp.i1))
        atEnd = offset + len(insertionString)
        self._parameters.append(self.addHighlight("", atEnd, atEnd))
        self.cycle(0)

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

    def cancel(self) -> None:
        for p in self._parameters:
            self._tc.removeExtraSelection(p.highlight)
        self._tc.updateExtraSelections()
        self._parameters.clear()
        self.parameterChanged.disconnect()

    def handleKeyPressed(self, obj: QObject, event: QKeyEvent):
        if self.getParametersSize() == 0:
            self.cancel()
            return False

        if event.type() == QEvent.KeyPress and obj is self._tc:
            if event.key() == Qt.Key_Tab or event.key() == Qt.Key_Return:
                self.next()
                event.accept()
                return True
            elif event.key() == Qt.Key_Backtab:
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
                ret.append(ParsedParam(varName, hlStart, hlEnd)) # hlEnd is exclusive
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

    def safeRemove(aList: list[str], entry: str):
        try:
            aList.remove(entry)
        except ValueError:
            pass

    parser.defineType("defined-channels", "'{channel:[A-Za-z0-9]:+}'",
            evaluator=None,
            autocompleter=Autocompleter(lambda e, justCheck: ";;;".join(definedChannels) if len(definedChannels) >= 1 else None))

    parser.defineType("defined-positions", "'{position:[A-Za-z0-9]:+}'",
            evaluator=Evaluator(lambda e: e.getParsedString("position")),
            autocompleter=Autocompleter(lambda e, justCheck: ";;;".join(definedRegions)))

    parser.defineType("time-unit", "second(s)", evaluator=Evaluator(lambda: 1))
    parser.defineType("time-unit", "minute(s)", evaluator=Evaluator(lambda: 60))
    parser.defineType("time-unit", "hour(s)",   evaluator=Evaluator(lambda: 3600))

    def inSeconds(e: ParsedNode):
        n = float(e.evaluate("n"))
        unit = int(e.evaluate("time-unit"))
        return round(n * unit)
    parser.defineType("time-interval", "{n:float} {time-unit:time-unit}", Evaluator(inSeconds), True)

    parser.defineType("repetition", "once", Evaluator(lambda e: [1, 0]))

    parser.defineType("repetition", "every {interval:time-interval} for {duration:time-interval}",
                      Evaluator(lambda e: [e.evaluate("interval"), e.evaluate("duration")]),
                      True)

    parser.defineType("z-distance", "{z-distance:float} microns", None, True)

    parser.defineType("lens",  "5x lens", None)
    parser.defineType("lens", "20x lens", None)

    parser.defineType("mag", "0.5x magnification changer", None)
    parser.defineType("mag", "1.0x magnification changer", None)
    parser.defineType("mag", "2.0x magnification changer", None)

    parser.defineType("binning", "1 x 1", evaluator=Evaluator(lambda: 1))
    parser.defineType("binning", "2 x 2", evaluator=Evaluator(lambda: 2))
    parser.defineType("binning", "3 x 3", evaluator=Evaluator(lambda: 3))
    parser.defineType("binning", "4 x 4", evaluator=Evaluator(lambda: 4))
    parser.defineType("binning", "5 x 5", evaluator=Evaluator(lambda: 5))

    parser.defineType("start", "At the beginning", None)
    parser.defineType("start", "At {time:time}", None, True)
    parser.defineType("start", "After {delay:time-interval}", None, True)

    parser.defineType("position-list", "all positions", None)
    parser.defineType("position-list", "position(s) {positions:list<defined-positions>}", None)

    parser.defineType("channel-list", "all channels", None)
    parser.defineType("channel-list", "channel(s) {channels:list<defined-channels>}", None)

    parser.defineSentence(
        "{star:start}{, }acquire..." +
        "{\n  }{repetition:repetition}" +
        "{\n  }{position-list:position-list}" +
        "{\n  }{channel-list:channel-list}" +
        # "{\n  }with a resolution of {dx:float} x {dy:float} x {dz:float} microns.",
        "{\n  }with a plane distance of {dz:z-distance}" +
        "{\n  }using the {lens:lens} with the {magnification:mag} and a binning of {binning:binning}",
        None)

    parser.defineSentence(
        "{start:start}{, }adjust..." +
        "{\n  }{repetition:repetition}" +
        "{\n  }the power of the {led:led} led of channel {channel:defined-channels} to {power:led-power}.",
        None)

    parser.defineSentence(
        "{start:start}{, }adjust..." +
        "{\n  }{repetition:repetition}" +
        "{\n  }the exposure time of channel {channel:defined-channels} to {exposure-time:exposure-time}.",
        None)

    parser.defineType("temperature", "{temperature:float}\u00B0C", None, True)
    parser.defineType("co2-concentration", "{CO2 concentration:float}%", None, True)

    parser.defineSentence(
        "{start:start}{, }adjust..." +
        "{\n  }{repetition:repetition}" +
        "{\n  }the CO2 concentration to {co2-concentration:co2-concentration}.",
        None)

    parser.defineSentence(
        "{start:start}{, }adjust..." +
        "{\n  }{repetition:repetition}" +
        "{\n  }the temperature to {temperature:temperature}.",
        None)

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

    import nls.autocompleter
    print("EntireSequenceAutocompleter called", nls.autocompleter.EntireSequenceAutocompleter.calledNTimes)

    print(",".join(map(lambda c: c.completion, autocompletions)))


if __name__ == "__main__":
    # doProfile()
    # testPathAutocompletion()
    # if True:
    #     exit(0)

    parser = initParser2()
    parser.compile()

    app = QApplication([])
    te = ACEditor(parser)
    te.show()
    exit(app.exec_())
