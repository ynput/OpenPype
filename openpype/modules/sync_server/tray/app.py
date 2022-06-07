from Qt import QtWidgets, QtCore, QtGui

from openpype.tools.settings import style

from openpype.lib import PypeLogger
from openpype import resources

from .widgets import (
    SyncProjectListWidget,
    SyncRepresentationSummaryWidget
)

log = PypeLogger().get_logger("SyncServer")


class SyncServerWindow(QtWidgets.QDialog):
    """
        Main window that contains list of synchronizable projects and summary
        view with all synchronizable representations for first project
    """

    def __init__(self, sync_server, parent=None):
        super(SyncServerWindow, self).__init__(parent)
        self.sync_server = sync_server
        self.setWindowFlags(QtCore.Qt.Window)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.setStyleSheet(style.load_stylesheet())
        self.setWindowIcon(QtGui.QIcon(resources.get_openpype_icon_filepath()))
        self.resize(1450, 700)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._hide_message)

        body = QtWidgets.QWidget(self)
        footer = QtWidgets.QWidget(self)
        footer.setFixedHeight(20)

        left_column = QtWidgets.QWidget(body)
        left_column_layout = QtWidgets.QVBoxLayout(left_column)

        self.projects = SyncProjectListWidget(sync_server, self)
        self.projects.refresh()  # force selection of default
        left_column_layout.addWidget(self.projects)
        self.pause_btn = QtWidgets.QPushButton("Pause server")

        left_column_layout.addWidget(self.pause_btn)

        checkbox = QtWidgets.QCheckBox("Show only enabled", self)
        checkbox.setStyleSheet("QCheckBox{spacing: 5px;"
                               "padding:5px 5px 5px 5px;}")
        checkbox.setChecked(True)
        self.show_only_enabled_chk = checkbox

        left_column_layout.addWidget(self.show_only_enabled_chk)

        repres = SyncRepresentationSummaryWidget(
            sync_server,
            project=self.projects.current_project,
            parent=self)
        container = QtWidgets.QWidget()
        container_layout = QtWidgets.QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        split = QtWidgets.QSplitter()
        split.addWidget(left_column)
        split.addWidget(repres)
        split.setSizes([180, 950, 200])
        container_layout.addWidget(split)

        body_layout = QtWidgets.QHBoxLayout(body)
        body_layout.addWidget(container)
        body_layout.setContentsMargins(0, 0, 0, 0)

        self.message = QtWidgets.QLabel(footer)
        self.message.hide()

        footer_layout = QtWidgets.QVBoxLayout(footer)
        footer_layout.addWidget(self.message)
        footer_layout.setContentsMargins(20, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(body)
        layout.addWidget(footer)

        self.setWindowTitle("Sync Queue")

        self.projects.project_changed.connect(
            self._on_project_change
        )

        self.pause_btn.clicked.connect(self._pause)
        self.pause_btn.setAutoDefault(False)
        self.pause_btn.setDefault(False)
        repres.message_generated.connect(self._update_message)
        self.projects.message_generated.connect(self._update_message)

        self.show_only_enabled_chk.stateChanged.connect(
            self._on_enabled_change
        )

        self.representationWidget = repres

    def showEvent(self, event):
        self.representationWidget.model.set_project(
            self.projects.current_project)
        self.projects.refresh()
        self._set_running(True)
        super().showEvent(event)

    def closeEvent(self, event):
        self._set_running(False)
        super().closeEvent(event)

    def _on_project_change(self):
        if self.projects.current_project is None:
            return

        self.representationWidget.table_view.model().set_project(
            self.projects.current_project
        )

        project_name = self.projects.current_project
        if not self.sync_server.get_sync_project_setting(project_name):
            self.projects.message_generated.emit(
                "Project {} not active anymore".format(project_name))
            self.projects.refresh()
            return

    def _on_enabled_change(self):
        """Called when enabled projects only checkbox is toggled."""
        self.projects.show_only_enabled = \
            self.show_only_enabled_chk.isChecked()
        self.projects.refresh()

    def _set_running(self, running):
        self.representationWidget.model.is_running = running
        self.representationWidget.model.timer.setInterval(0)

    def _pause(self):
        if self.sync_server.is_paused():
            self.sync_server.unpause_server()
            self.pause_btn.setText("Pause server")
        else:
            self.sync_server.pause_server()
            self.pause_btn.setText("Unpause server")
        self.projects.refresh()

    def _update_message(self, value):
        """
            Update and show message in the footer
        """
        self.message.setText(value)
        if self.message.isVisible():
            self.message.repaint()
        else:
            self.message.show()
        msec_delay = 3000
        self.timer.start(msec_delay)

    def _hide_message(self):
        """
            Hide message in footer

            Called automatically by self.timer after a while
        """
        self.message.setText("")
        self.message.hide()
