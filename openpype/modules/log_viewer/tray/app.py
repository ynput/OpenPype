from Qt import QtWidgets, QtCore
from .widgets import LogsWidget, OutputWidget
from openpype import style


class LogsWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(LogsWindow, self).__init__(parent)

        self.setWindowTitle("Logs viewer")

        self.resize(1400, 800)
        log_detail = OutputWidget(parent=self)
        logs_widget = LogsWidget(log_detail, parent=self)

        main_layout = QtWidgets.QHBoxLayout(self)

        log_splitter = QtWidgets.QSplitter(self)
        log_splitter.setOrientation(QtCore.Qt.Horizontal)
        log_splitter.addWidget(logs_widget)
        log_splitter.addWidget(log_detail)

        main_layout.addWidget(log_splitter)

        self.logs_widget = logs_widget
        self.log_detail = log_detail

        self.setStyleSheet(style.load_stylesheet())

        self._first_show = True

    def showEvent(self, event):
        super(LogsWindow, self).showEvent(event)

        if self._first_show:
            self._first_show = False
            self.logs_widget.refresh()
