from Qt import QtWidgets, QtCore
from .widgets import LogsWidget, LogDetailWidget
from avalon import style


class LogsWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(LogsWindow, self).__init__(parent)

        self.setStyleSheet(style.load_stylesheet())
        self.resize(1200, 800)
        logs_widget = LogsWidget(parent=self)
        log_detail = LogDetailWidget(parent=self)

        main_layout = QtWidgets.QHBoxLayout()

        log_splitter = QtWidgets.QSplitter()
        log_splitter.setOrientation(QtCore.Qt.Horizontal)
        log_splitter.addWidget(logs_widget)
        log_splitter.addWidget(log_detail)
        log_splitter.setStretchFactor(0, 65)
        log_splitter.setStretchFactor(1, 35)

        main_layout.addWidget(log_splitter)

        self.logs_widget = logs_widget
        self.log_detail = log_detail

        self.setLayout(main_layout)
        self.setWindowTitle("Logs")

        self.logs_widget.active_changed.connect(self.on_selection_changed)

    def on_selection_changed(self):
        index = self.logs_widget.selected_log()
        if not index or not index.isValid():
            return
        node = index.data(self.logs_widget.model.NodeRole)
        self.log_detail.set_detail(node)
