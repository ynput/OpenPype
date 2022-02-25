"""Tray publisher is extending publisher tool.

Adds ability to select project using overlay widget with list of projects.

Tray publisher can be considered as host implementeation with creators and
publishing plugins.
"""

from Qt import QtWidgets, QtCore

import avalon.api
from avalon.api import AvalonMongoDB
from openpype.hosts.traypublisher import (
    api as traypublisher
)
from openpype.tools.publisher import PublisherWindow
from openpype.tools.utils.constants import PROJECT_NAME_ROLE
from openpype.tools.utils.models import (
    ProjectModel,
    ProjectSortFilterProxy
)


class StandaloneOverlayWidget(QtWidgets.QFrame):
    project_selected = QtCore.Signal(str)

    def __init__(self, publisher_window):
        super(StandaloneOverlayWidget, self).__init__(publisher_window)
        self.setObjectName("OverlayFrame")

        # Create db connection for projects model
        dbcon = AvalonMongoDB()
        dbcon.install()

        header_label = QtWidgets.QLabel("Choose project", self)
        header_label.setObjectName("ChooseProjectLabel")
        # Create project models and view
        projects_model = ProjectModel(dbcon)
        projects_proxy = ProjectSortFilterProxy()
        projects_proxy.setSourceModel(projects_model)

        projects_view = QtWidgets.QListView(self)
        projects_view.setModel(projects_proxy)
        projects_view.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )

        confirm_btn = QtWidgets.QPushButton("Choose", self)
        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.addStretch(1)
        btns_layout.addWidget(confirm_btn, 0)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(header_label, 0, 1, alignment=QtCore.Qt.AlignCenter)
        layout.addWidget(projects_view, 1, 1)
        layout.addLayout(btns_layout, 2, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 1)
        layout.setRowStretch(0, 0)
        layout.setRowStretch(1, 1)
        layout.setRowStretch(2, 0)

        projects_view.doubleClicked.connect(self._on_double_click)
        confirm_btn.clicked.connect(self._on_confirm_click)

        self._projects_view = projects_view
        self._projects_model = projects_model
        self._confirm_btn = confirm_btn

        self._publisher_window = publisher_window

    def showEvent(self, event):
        self._projects_model.refresh()
        super(StandaloneOverlayWidget, self).showEvent(event)

    def _on_double_click(self):
        self.set_selected_project()

    def _on_confirm_click(self):
        self.set_selected_project()

    def set_selected_project(self):
        index = self._projects_view.currentIndex()

        project_name = index.data(PROJECT_NAME_ROLE)
        if not project_name:
            return

        traypublisher.set_project_name(project_name)
        self.setVisible(False)
        self.project_selected.emit(project_name)


class TrayPublishWindow(PublisherWindow):
    def __init__(self, *args, **kwargs):
        super(TrayPublishWindow, self).__init__(reset_on_show=False)

        overlay_widget = StandaloneOverlayWidget(self)

        btns_widget = QtWidgets.QWidget(self)

        back_to_overlay_btn = QtWidgets.QPushButton(
            "Change project", btns_widget
        )
        save_btn = QtWidgets.QPushButton("Save", btns_widget)
        # TODO implement save mechanism of tray publisher
        save_btn.setVisible(False)

        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)

        btns_layout.addWidget(save_btn, 0)
        btns_layout.addWidget(back_to_overlay_btn, 0)

        self._header_layout.addWidget(btns_widget, 0)

        overlay_widget.project_selected.connect(self._on_project_select)
        back_to_overlay_btn.clicked.connect(self._on_back_to_overlay)
        save_btn.clicked.connect(self._on_tray_publish_save)

        self._back_to_overlay_btn = back_to_overlay_btn
        self._overlay_widget = overlay_widget

    def _on_back_to_overlay(self):
        self._overlay_widget.setVisible(True)
        self._resize_overlay()

    def _resize_overlay(self):
        self._overlay_widget.resize(
            self.width(),
            self.height()
        )

    def resizeEvent(self, event):
        super(TrayPublishWindow, self).resizeEvent(event)
        self._resize_overlay()

    def _on_project_select(self, project_name):
        # TODO register project specific plugin paths
        self.controller.save_changes()
        self.controller.reset_project_data_cache()

        self.reset()
        if not self.controller.instances:
            self._on_create_clicked()

    def _on_tray_publish_save(self):
        self.controller.save_changes()
        print("NOT YET IMPLEMENTED")


def main():
    avalon.api.install(traypublisher)
    app = QtWidgets.QApplication([])
    window = TrayPublishWindow()
    window.show()
    app.exec_()
