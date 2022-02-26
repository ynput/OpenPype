from avalon import style
from Qt import QtWidgets, QtCore
import collections
import re


class ConsoleDialog(QtWidgets.QDialog):
    """Qt dialog to show stdout instead of unwieldy cmd window"""
    WIDTH = 720
    HEIGHT = 450
    MAX_LINES = 10000

    sdict = {
        r">>> ":
            '<span style="font-weight: bold;color:#EE5C42"> >>> </span>',
        r"!!!(?!\sCRI|\sERR)":
            '<span style="font-weight: bold;color:red"> !!! </span>',
        r"\-\-\- ":
            '<span style="font-weight: bold;color:cyan"> --- </span>',
        r"\*\*\*(?!\sWRN)":
            '<span style="font-weight: bold;color:#FFD700"> *** </span>',
        r"\*\*\* WRN":
            '<span style="font-weight: bold;color:#FFD700"> *** WRN</span>',
        r"  \- ":
            '<span style="font-weight: bold;color:#FFD700">  - </span>',
        r"\[ ":
            '<span style="font-weight: bold;color:#66CDAA">[</span>',
        r"\]":
            '<span style="font-weight: bold;color:#66CDAA">]</span>',
        r"{":
            '<span style="color:#66CDAA">{',
        r"}":
            r"}</span>",
        r"\(":
            '<span style="color:#66CDAA">(',
        r"\)":
            r")</span>",
        r"^\.\.\. ":
            '<span style="font-weight: bold;color:#EE5C42"> ... </span>',
        r"!!! ERR: ":
            '<span style="font-weight: bold;color:#EE5C42"> !!! ERR: </span>',
        r"!!! CRI: ":
            '<span style="font-weight: bold;color:red"> !!! CRI: </span>',
        r"(?i)failed":
            '<span style="font-weight: bold;color:#EE5C42"> FAILED </span>',
        r"(?i)error":
            '<span style="font-weight: bold;color:#EE5C42"> ERROR </span>'
    }

    def __init__(self, text, parent=None):
        super(ConsoleDialog, self).__init__(parent)
        layout = QtWidgets.QHBoxLayout(parent)

        plain_text = QtWidgets.QPlainTextEdit(self)
        plain_text.setReadOnly(True)
        plain_text.resize(self.WIDTH, self.HEIGHT)
        plain_text.maximumBlockCount = self.MAX_LINES

        while text:
            plain_text.appendPlainText(text.popleft().strip())

        layout.addWidget(plain_text)

        self.setWindowTitle("Console output")

        self.plain_text = plain_text

        self.setStyleSheet(style.load_stylesheet())

        self.resize(self.WIDTH, self.HEIGHT)

    def append_text(self, new_text):
        if isinstance(new_text, str):
            new_text = collections.deque(new_text.split("\n"))
        while new_text:
            text = new_text.popleft()
            if text:
                self.plain_text.appendHtml(self.color(text))

    def _multiple_replace(self, text, adict):
        """Replace multiple tokens defined in dict.

        Find and replace all occurrences of strings defined in dict is
        supplied string.

        Args:
            text (str): string to be searched
            adict (dict): dictionary with `{'search': 'replace'}`

        Returns:
            str: string with replaced tokens

        """
        for r, v in adict.items():
            text = re.sub(r, v, text)

        return text

    def color(self, message):
        """Color message with html tags. """
        message = self._multiple_replace(message, self.sdict)

        return message
