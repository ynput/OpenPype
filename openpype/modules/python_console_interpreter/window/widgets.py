import os
import sys
from code import InteractiveInterpreter

from Qt import QtCore, QtWidgets, QtGui

from openpype.style import load_stylesheet


class MultipleRedirection:
    """ Dummy file which redirects stream to multiple file """

    def __init__(self, *files):
        """ The stream is redirect to the file list 'files' """

        self.files = files

    def write(self, line):
        """ Emulate write function """

        for _file in self.files:
            _file.write(line)


class StringObj:
    def __init__(self, text=None):
        if isinstance(text, StringObj):
            text = str(text)

        self._text = text or ""

    def __str__(self):
        return self._text

    def __len__(self):
        return self.length()

    def __bool__(self):
        return bool(self._text)

    def length(self):
        return len(self._text)

    def clear(self):
        self._text = ""

    def insert(self, point, text):
        if isinstance(text, StringObj):
            text = str(text)
        self._text = self._text[:point] + text + self._text[point:]

    def remove(self, point, count):
        self._text = self._text[:point] + self._text[point + count:]

    def copy(self):
        return StringObj(self._text)


class PythonInterpreterWidget(QtWidgets.QTextEdit):
    def __init__(self, parent=None):
        super(PythonInterpreterWidget, self).__init__(parent)

        self.setObjectName("PythonInterpreterWidget")
        self._indent = 4

        self._interpreter = InteractiveInterpreter()

        # to exit the main interpreter by a Ctrl-D if PyCute has no parent
        if parent is None:
            self.eofKey = QtCore.Qt.Key_D
        else:
            self.eofKey = None

        # capture all interactive input/output
        sys.stdout = MultipleRedirection(sys.stdout, self)
        sys.stderr = MultipleRedirection(sys.stderr, self)

        # last line + last incomplete lines
        self.line = StringObj()
        self.lines = []
        # the cursor position in the last line
        self.point = 0
        # flag: the interpreter needs more input to run the last lines.
        self.more = False
        # flag: readline() is being used for e.g. raw_input() and input()
        self.reading = False
        # history
        self.history = []
        self.pointer = 0
        self.cursor_pos = 0

        # user interface setup
        self.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)

        self.setStyleSheet(load_stylesheet())

        # interpreter prompt.
        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = ">>> "
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = "... "

        # interpreter banner
        self.write("The shell running Python {} on {}.\n".format(
            sys.version, sys.platform
        ))
        self.write((
            "Type \"copyright\", \"credits\" or \"license\""
            " for more information on Python.\n"
        ))
        self.write("\nWelcome to OpenPype!\n\n")
        self.write(sys.ps1)

    @property
    def interpreter(self):
        """Interpreter object."""
        return self._interpreter

    def moveCursor(self, operation, mode=None):
        if mode is None:
            mode = QtGui.QTextCursor.MoveAnchor
        cursor = self.textCursor()
        cursor.movePosition(operation, mode)
        self.setTextCursor(cursor)

    def flush(self):
        """Simulate stdin, stdout, and stderr flush."""
        pass

    def isatty(self):
        """Simulate stdin, stdout, and stderr isatty."""
        return 1

    def readline(self):
        """Simulate stdin, stdout, and stderr readline."""
        self.reading = True
        self.__clearLine()
        self.moveCursor(QtGui.QTextCursor.End)
        while self.reading:
            QtWidgets.QApplication.processOneEvent()
        if self.line.length() == 0:
            return "\n"
        return str(self.line)

    def write(self, text):
        """Simulate stdin, stdout, and stderr write."""
        cursor = self.textCursor()

        cursor.movePosition(QtGui.QTextCursor.End)

        # pos1 = cursor.position()
        cursor.insertText(str(text))

        self.cursor_pos = cursor.position()
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

        # Set the format
        # cursor.setPosition(pos1, QtGui.QTextCursor.KeepAnchor)
        # char_format = cursor.charFormat()
        # char_format.setForeground(QtGui.QBrush(QtGui.QColor(0, 0, 0)))
        # cursor.setCharFormat(char_format)

    def writelines(self, text):
        """
        Simulate stdin, stdout, and stderr.
        """
        for line in text.split("\n"):
            self.write(line)

    def fake_user_input(self, lines):
        """Simulate a user input lines is a sequence of strings.

        Args:
            lines(list, tuple): Lines to process.
        """
        for line in lines:
            self.line = StringObj(line.rstrip())
            self.write(self.line)
            self.write("\n")
            self.__run()

    def __run(self):
        """
        Append the last line to the history list, let the interpreter execute
        the last line(s), and clean up accounting for the interpreter results:
        (1) the interpreter succeeds
        (2) the interpreter fails, finds no errors and wants more line(s)
        (3) the interpreter fails, finds errors and writes them to sys.stderr
        """
        self.pointer = 0
        self.history.append(self.line.copy())
        try:
            self.lines.append(str(self.line))
        except Exception as exc:
            print(exc)

        source = "\n".join(self.lines)
        self.more = self._interpreter.runsource(source)
        if self.more:
            self.write(sys.ps2)
        else:
            self.write(sys.ps1)
            self.lines = []
        self.__clearLine()

    def __clearLine(self):
        """Clear input line buffer."""
        self.line.clear()
        self.point = 0

    def __insertText(self, text):
        """Insert text at the current cursor position."""

        self.line.insert(self.point, text)
        self.point += len(text)

        cursor = self.textCursor()
        cursor.insertText(str(text))

    def keyPressEvent(self, event):
        """Handle user input a key at a time."""
        text = event.text()
        key = event.key()

        if key == QtCore.Qt.Key_Backspace:
            if self.point:
                cursor = self.textCursor()
                cursor.movePosition(
                    QtGui.QTextCursor.PreviousCharacter,
                    QtGui.QTextCursor.KeepAnchor
                )
                cursor.removeSelectedText()

                self.point -= 1

                self.line.remove(self.point, 1)

        elif key == QtCore.Qt.Key_Delete:
            cursor = self.textCursor()
            cursor.movePosition(
                QtGui.QTextCursor.NextCharacter,
                QtGui.QTextCursor.KeepAnchor
            )
            cursor.removeSelectedText()

            self.line.remove(self.point, 1)

        elif key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.write("\n")
            if self.reading:
                self.reading = False
            else:
                self.__run()

        elif key == QtCore.Qt.Key_Tab:
            self.__insertText(" " * self._indent)

        elif key == QtCore.Qt.Key_Left:
            if self.point:
                self.moveCursor(QtGui.QTextCursor.Left)
                self.point -= 1
        elif key == QtCore.Qt.Key_Right:
            if self.point < self.line.length():
                self.moveCursor(QtGui.QTextCursor.Right)
                self.point += 1

        elif key == QtCore.Qt.Key_Home:
            cursor = self.textCursor()
            cursor.setPosition(self.cursor_pos)
            self.setTextCursor(cursor)
            self.point = 0

        elif key == QtCore.Qt.Key_End:
            self.moveCursor(QtGui.QTextCursor.EndOfLine)
            self.point = self.line.length()

        elif key == QtCore.Qt.Key_Up:
            if self.history:
                if self.pointer == 0:
                    self.pointer = len(self.history)
                self.pointer -= 1
                self.__recall()

        elif key == QtCore.Qt.Key_Down:
            if self.history:
                self.pointer += 1
                if self.pointer == len(self.history):
                    self.pointer = 0
                self.__recall()

        elif text:
            self.__insertText(text)
            return

        else:
            event.ignore()

    def __recall(self):
        """Display the current item from the command history."""
        cursor = self.textCursor()
        cursor.select(QtGui.QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()

        if self.more:
            self.write(sys.ps2)
        else:
            self.write(sys.ps1)

        self.__clearLine()
        self.__insertText(self.history[self.pointer])

    def mousePressEvent(self, event):
        """Keep the cursor after the last prompt."""
        if event.button() == QtCore.Qt.LeftButton:
            self.moveCursor(QtGui.QTextCursor.End)

    def contentsContextMenuEvent(self, event):
        """Suppress the right button context menu."""
        pass
