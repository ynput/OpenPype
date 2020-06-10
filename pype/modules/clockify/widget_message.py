from Qt import QtCore, QtGui, QtWidgets
from avalon import style


class MessageWidget(QtWidgets.QWidget):

    SIZE_W = 300
    SIZE_H = 130

    closed = QtCore.Signal()

    def __init__(self, parent=None, messages=[], title="Message"):

        super(MessageWidget, self).__init__()

        self._parent = parent

        # Icon
        if parent and hasattr(parent, 'icon'):
            self.setWindowIcon(parent.icon)
        else:
            from pypeapp.resources import get_resource
            self.setWindowIcon(QtGui.QIcon(get_resource('icon.png')))

        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint
        )

        # Font
        self.font = QtGui.QFont()
        self.font.setFamily("DejaVu Sans Condensed")
        self.font.setPointSize(9)
        self.font.setBold(True)
        self.font.setWeight(50)
        self.font.setKerning(True)

        # Size setting
        self.resize(self.SIZE_W, self.SIZE_H)
        self.setMinimumSize(QtCore.QSize(self.SIZE_W, self.SIZE_H))
        self.setMaximumSize(QtCore.QSize(self.SIZE_W+100, self.SIZE_H+100))

        # Style
        self.setStyleSheet(style.load_stylesheet())

        self.setLayout(self._ui_layout(messages))
        self.setWindowTitle(title)

    def _ui_layout(self, messages):
        if not messages:
            messages = ["*Misssing messages (This is a bug)*", ]

        elif not isinstance(messages, (tuple, list)):
            messages = [messages, ]

        main_layout = QtWidgets.QVBoxLayout(self)

        labels = []
        for message in messages:
            label = QtWidgets.QLabel(message)
            label.setFont(self.font)
            label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            label.setTextFormat(QtCore.Qt.RichText)
            label.setWordWrap(True)

            labels.append(label)
            main_layout.addWidget(label)

        btn_close = QtWidgets.QPushButton("Close")
        btn_close.setToolTip('Close this window')
        btn_close.clicked.connect(self.on_close_clicked)

        btn_group = QtWidgets.QHBoxLayout()
        btn_group.addStretch(1)
        btn_group.addWidget(btn_close)

        main_layout.addLayout(btn_group)

        self.labels = labels
        self.btn_group = btn_group
        self.btn_close = btn_close
        self.main_layout = main_layout

        return main_layout

    def on_close_clicked(self):
        self.close()

    def close(self, *args, **kwargs):
        self.closed.emit()
        super(MessageWidget, self).close(*args, **kwargs)
