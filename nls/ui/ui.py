from __future__ import annotations

import sys
import time
import traceback
from typing import cast, List, Callable

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, QStringListModel, QRect, QObject, QEvent, QModelIndex, pyqtSignal, pyqtSlot, \
    QThreadPool, QRunnable
from PyQt5.QtGui import QTextCursor, QKeyEvent, QColor, QPalette, QFont
from PyQt5.QtWidgets import QCompleter, QPlainTextEdit, QApplication, QTextEdit, QItemDelegate, QStyleOptionViewItem, \
    QWidget, QSplitter, QPushButton, QVBoxLayout

from nls.core import graphviz
from nls.core.autocompletion import Autocompletion, Literal, Parameterized, EntireSequence, Purpose
from nls.core.bnf import BNF
from nls.core.matcher import Matcher
from nls.core.nonterminal import NonTerminal
from nls.core.symbol import Symbol
from nls.ebnf.rule import Rule
from nls.parsednode import ParsedNode
from nls.parseexception import ParseException
from nls.parser import Parser
from nls.ui.codeeditor import CodeEditor


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)


class Worker(QRunnable):
    """
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    """

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(
                *self.args, **self.kwargs
            )
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


class ACEditor(QWidget):

    work_requested = pyqtSignal(int)

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

        self.runButton = QPushButton("Run", self)
        self.runButton.clicked.connect(self.run)
        vbox.addWidget(self.runButton, alignment=Qt.AlignCenter)

        self.setLayout(vbox)
        self.resize(800, 600)

        self._beforeRun: Callable[[], None] = lambda: None
        self._afterRun: Callable[[], None] = lambda: None

        self.threadpool = QThreadPool()

    def setBeforeRun(self, beforeRun: Callable[[], None]) -> None:
        self._beforeRun = beforeRun

    def setAfterRun(self, afterRun: Callable[[], None]) -> None:
        self._afterRun = afterRun

    def getText(self) -> str:
        return self._textEdit.document().toPlainText()

    def getSelectedLinesStart(self) -> str:
        tc: QTextCursor = self._textEdit.textCursor()
        start: int = tc.selectionStart()
        tc.setPosition(start)
        tc.movePosition(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
        return tc.position()

    def getSelectedLines(self) -> str:
        tc: QTextCursor = self._textEdit.textCursor()
        start: int = tc.selectionStart()
        end: int = tc.selectionEnd()
        tc.setPosition(start)
        tc.movePosition(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
        tc.setPosition(end, QTextCursor.KeepAnchor)
        tc.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        selected: str = tc.selection().toPlainText()
        return selected

    def run(self, selectedLines: bool = False) -> None:
        self._outputArea.setPlainText("")
        self.runButton.setEnabled(False)
        textToEvaluate = self.getSelectedLines() if selectedLines else self.getText()
        worker = Worker(self.run_fn, self._parser, textToEvaluate)
        worker.signals.finished.connect(lambda: self.runButton.setEnabled(True))
        worker.signals.error.connect(lambda exc: self._outputArea.setPlainText(
            exc[1].getError() if isinstance(exc[1], ParseException) else exc[2]
        ))
        self.threadpool.start(worker)

    def run_fn(self, parser: Parser, textToEvaluate: str) -> None:
        self._beforeRun()
        print("Parsing...")
        pn: ParsedNode = parser.parse(textToEvaluate)
        print(graphviz.toVizDotLink(pn))
        print("Evaluating...")
        pn.evaluate()
        self._afterRun()
        print("Done")


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
    def __init__(self, parser: Parser, parent=None):
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

    def insertCompletion(self, completion: Autocompletion) -> None:
        tc = self.textCursor()

        entireText = self.toPlainText()
        caret = self.textCursor().position()
        cursorIsAtEnd = caret == len(entireText) or len(entireText[caret:].strip()) == 0

        # select the previous len(completionPrefix) characters:
        tc.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, len(self.completer.completionPrefix()))

        repl: str = completion.getCompletion(Purpose.FOR_INSERTION)

        try:
            repl.index("${")  # throws ValueError if '${' does not exist in completion
            self.cancelParameterizedCompletion()
            self.parameterizedCompletion = ParameterizedCompletionContext(tc=self)
            self.parameterizedCompletion.parameterChanged.connect(self.parameterChanged)
            self.parameterizedCompletion.replaceSelection(completion)
        except ValueError:
            # self.cancelParameterizedCompletion()
            tc.removeSelectedText()
            tc.insertText(repl)
            self.completer.popup().hide()
            if cursorIsAtEnd:
                self.autocomplete()

    def parameterChanged(self, _pIdx: int, wasLast: bool) -> None:
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
        rect = self.cursorRect(c)
        c.setPosition(p)
        r = self.cursorRect(c)
        rect.setRight(r.right())
        return rect

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
            if event.key() == Qt.Key_Escape:
                self.cancelParameterizedCompletion()
                return
            if self.parameterizedCompletion.handleKeyPressed(self, event):
                return

        if self.completer.popup().isVisible() and event.key() == Qt.Key.Key_Tab:
            self.completer.popup().hide()
            return

        QPlainTextEdit.keyPressEvent(self, event)

        etext = event.text()
        if len(etext) > 0 and etext.isprintable():
            self.autocomplete()

    def autocomplete(self, autoinsertSingleOption: bool = True):
        cursor = self.textCursor()
        cursor.setPosition(cursor.anchor())
        cr = self.cursorRect(cursor)

        entireText = self.toPlainText()
        anchor = self.textCursor().anchor()

        textToCursor = entireText[0:anchor]
        autocompletions: List[Autocompletion] = []

        self._errorHighlight.clearError()
        try:
            self.parser.parse(textToCursor, autocompletions)
        except ParseException as e:
            f: Matcher = e.getFirstAutocompletingAncestorThatFailed().matcher
            self._errorHighlight.setError(f.pos, f.pos + len(f.parsed))
            return

        # we are in a parameterized completion context.
        # we still want to autocomplete, but not beyond the end of the current parameter
        bnf: BNF = self.parser.targetGrammar.getBNF()
        if self.parameterizedCompletion is not None:
            if len(autocompletions) > 0:
                atLeastOneCompletionForCurrentParameter: bool = False
                for comp in autocompletions:
                    symbol = comp.forSymbol

                    # if comp is an EntireSequence completion, we should just check the first
                    # we can do that using ParameterizedCompletionContext.parseParameters
                    if isinstance(comp, EntireSequence):
                        tmp: List[ParsedParam] = []
                        ParameterizedCompletionContext.parseParameters(comp, tmp, 0)
                        comp = tmp[0].autocompletion
                        symbol = comp.forSymbol

                    if symbol == self.parameterizedCompletion.getForAutocompletion().forSymbol:
                        atLeastOneCompletionForCurrentParameter = True
                        break

                    # check if symbol is a descendent of the parameters autocompletion symbol
                    parameterSymbol: Symbol = self.parameterizedCompletion.getCurrentParameter().autocompletion.forSymbol
                    # symbol == parameterSymbol? -> fine
                    if symbol == parameterSymbol:
                        atLeastOneCompletionForCurrentParameter = True
                        break

                    if isinstance(parameterSymbol, NonTerminal):
                        #  check recursively if symbol is in the list of child symbols
                        if cast(NonTerminal, parameterSymbol).uses(symbol, bnf):
                            atLeastOneCompletionForCurrentParameter = True
                            break

                if not atLeastOneCompletionForCurrentParameter:
                    self.parameterizedCompletion.next()
                    return
            else:
                print("no completions")
        else:
            print("parameterized completion = None")

        if len(autocompletions) == 1:
            if autoinsertSingleOption or isinstance(autocompletions[0], Literal):
                self.completer.setCompletions(autocompletions)
                alreadyEntered = autocompletions[0].getAlreadyEnteredText()
                self.completer.setCompletionPrefix(alreadyEntered)
                self.insertCompletion(autocompletions[0])
        elif len(autocompletions) > 1:
            self.completer.setCompletions(autocompletions)
            alreadyEntered = autocompletions[0].getAlreadyEnteredText()
            self.completer.setCompletionPrefix(alreadyEntered)

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
            ret = c.getCompletion(Purpose.FOR_MENU)
            # parsedParams = []
            # ParameterizedCompletionContext.parseParameters(c, parsedParams)
            if ret.startswith("\n"):
                ret = "<new line>"  # "<strong>new</strong> line"
            if ret == "":
                ret = "<empty>"
            return ret

        cast(QStringListModel, self.model()).setStringList(map(printNice, completions))

    def selectionChanged(self, idx: QModelIndex) -> None:
        self.lastSelected = idx.row()

    def getSelected(self) -> Autocompletion or None:
        return None if self.lastSelected < 0 else self._completions[self.lastSelected]


class ParameterizedCompletionContext(QObject):
    parameterChanged = QtCore.pyqtSignal(int, bool)

    def __init__(self, tc: CodeEditor):
        super().__init__(parent=tc)
        self._tc = tc
        self._parameters: List[Param] = []
        self._forAutocompletion: Autocompletion or None = None

    @property
    def parameters(self) -> List[Param]:
        return self._parameters

    def printHighlights(self):
        for p in self._parameters:
            print(str(p))

    def addHighlight(self, name: str, autocompletion: Autocompletion or None, i0: int, i1: int) -> Param:
        selection = QTextEdit.ExtraSelection()

        cursor = self._tc.textCursor()
        cursor.setPosition(i0 - 1)
        cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, i1 - i0 + 1)
        selection.cursor = cursor

        self._tc.addExtrasSelection(selection)
        self._tc.updateExtraSelections()

        param = Param(name, autocompletion, selection)
        return param

    def getForAutocompletion(self) -> Autocompletion:
        return self._forAutocompletion

    def replaceSelection(self, autocompletion: Autocompletion) -> None:
        self._forAutocompletion = autocompletion
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
            self._parameters.append(self.addHighlight(pp.name, pp.autocompletion, offset + pp.i0, offset + pp.i1))
        atEnd = offset + len(insertionString)
        self._parameters.append(self.addHighlight("", None, atEnd, atEnd))
        self.cycle(0)

    def getParametersSize(self):
        return len(self._parameters)

    def getPreviousParameterIndexForCursorPosition(self, pos: int) -> int:
        reverse_it = reversed(list(enumerate(self._parameters)))
        return next((i for i, param in reverse_it if pos > param.highlight.cursor.position()), -1)

    def getNextParameterIndexForCursorPosition(self, pos: int) -> int:
        return next((i for i, param in enumerate(self._parameters) if pos < param.highlight.cursor.anchor() + 1), -1)

    def getParamIndexForCursorPosition(self, pos: int) -> int:
        return next((i for i, param in enumerate(self._parameters) if
              param.highlight.cursor.anchor() + 1 <= pos <= param.highlight.cursor.position()), -1)

    def getCurrentParameter(self) -> Param:
        idx = self.getParamIndexForCursorPosition(self._tc.textCursor().position())
        print("Current paramter index is " + str(idx))
        return self.parameters[idx] if idx >= 0 else None

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
        return False

    @staticmethod
    def parseParameters(autocompletion: Autocompletion, ret: List[ParsedParam], offset: int = 0) -> str:
        if isinstance(autocompletion, Literal):
            return autocompletion.getCompletion(Purpose.FOR_INSERTION)

        if isinstance(autocompletion, Parameterized):
            s = cast(Parameterized, autocompletion).paramName
            ret.append(ParsedParam(s, 0, len(s), autocompletion))
            return s

        if isinstance(autocompletion, EntireSequence):
            entireSequence: EntireSequence = cast(EntireSequence, autocompletion)
            sequenceOfCompletions: List[List[Autocompletion]] = entireSequence.getSequenceOfCompletions()
            sequence: Rule = autocompletion.getSequence()
            insertionString: str = ""
            for i, autocompletions in enumerate(sequenceOfCompletions):
                n: int = len(autocompletions)
                if n > 1:
                    name: str = sequence.getNameForChild(i)
                    p: Parameterized = Parameterized(forSymbol=sequence.children[i], symbolName=name, paramName=name)
                    i0: int = offset + len(insertionString)
                    i1: int = i0 + len(name)
                    ret.append(ParsedParam(name, i0, i1, p))
                    insertionString += name
                elif n == 1:
                    single: Autocompletion = autocompletions[0]
                    if isinstance(single, Literal):
                        insertionString += single.getCompletion(Purpose.FOR_INSERTION)
                    elif isinstance(single, Parameterized):
                        parameterized: Parameterized = cast(Parameterized, single)
                        s = parameterized.paramName
                        i0: int = offset + len(insertionString)
                        i1 = i0 + len(s)
                        ret.append(ParsedParam(s, i0, i1, parameterized))
                        insertionString += s
                    elif isinstance(single, EntireSequence):
                        entire: EntireSequence = cast(EntireSequence, single)
                        offs: int = offset + len(insertionString)
                        s = ParameterizedCompletionContext.parseParameters(entire, ret, offs)
                        insertionString += s
                    else:
                        print("Unknown/unexpected autocompletion")
            return insertionString

        raise Exception("Unexpected completion type: " + str(type(autocompletion)))


class ParsedParam:
    def __init__(self, name: str, i0: int, i1: int, autocompletion: Autocompletion):
        self._name = name
        self._i0 = i0
        self._i1 = i1
        self._autocompletion = autocompletion

    @property
    def i0(self) -> int:
        return self._i0

    @property
    def i1(self) -> int:
        return self._i1

    @property
    def name(self) -> str:
        return self._name

    @property
    def autocompletion(self) -> Autocompletion:
        return self._autocompletion


class Param:
    def __init__(self, name: str, autocompletion: Autocompletion, selection: QTextEdit.ExtraSelection):
        self._name = name
        self._autocompletion = autocompletion
        self._highlight = selection

    @property
    def name(self):
        return self._name

    @property
    def highlight(self):
        return self._highlight

    @property
    def autocompletion(self):
        return self._autocompletion

    def __str__(self):
        c = self._highlight.cursor
        return "{} : [{}, {}[".format(self._name, c.anchor(), c.position())


def initParser():
    parser = Parser()
    parser.defineType("color", "blue", None)
    parser.defineType("color", "green", None)
    parser.defineSentence("My favorite color is {color:color}.", None)
    return parser


def doProfile():
    parser = initParser()
    parser.compile()

    textToCursor = "My favorite"
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


def main():
    # doProfile()
    # testPathAutocompletion()
    # if True:
    #     exit(0)

    parser = initParser()
    parser.compile()

    app = QApplication([])
    te = ACEditor(parser)
    te.show()
    exit(app.exec_())


if __name__ == "__main__":
    main()
