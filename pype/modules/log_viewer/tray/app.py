from Qt import QtWidgets, QtCore
from .widgets import LogsWidget, OutputWidget
from avalon import style


class LogsWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(LogsWindow, self).__init__(parent)

        self.setStyleSheet(style.load_stylesheet())
        self.resize(1400, 800)
        log_detail = OutputWidget(parent=self)
        logs_widget = LogsWidget(log_detail, parent=self)

        main_layout = QtWidgets.QHBoxLayout()

        log_splitter = QtWidgets.QSplitter()
        log_splitter.setOrientation(QtCore.Qt.Horizontal)
        log_splitter.addWidget(logs_widget)
        log_splitter.addWidget(log_detail)

        main_layout.addWidget(log_splitter)

        self.logs_widget = logs_widget
        self.log_detail = log_detail

        self.setLayout(main_layout)
        self.setWindowTitle("Logs")
