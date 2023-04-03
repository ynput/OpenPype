"""Tray publisher is extending publisher tool.

Adds ability to select project using overlay widget with list of projects.

Tray publisher can be considered as host implementeation with creators and
publishing plugins.
"""

import platform

from qtpy import QtWidgets, QtCore
import qtawesome
import appdirs

from openpype.lib import JSONSettingRegistry
from openpype.pipeline import install_host
from openpype.hosts.traypublisher.api import TrayPublisherHost
from openpype.tools.publisher.control_qt import QtPublisherController
from openpype.tools.publisher.window import PublisherWindow
from openpype.tools.utils import PlaceholderLineEdit
from openpype.tools.utils.constants import PROJECT_NAME_ROLE
from openpype.tools.utils.models import (
    ProjectModel,
    ProjectSortFilterProxy
)


class TrayPublisherController(QtPublisherController):
    @property
    def host(self):
        return self._host

    def reset_project_data_cache(self):
        self._asset_docs_cache.reset()


class TrayPublisherRegistry(JSONSettingRegistry):
    """Class handling OpenPype general settings registry.

    Attributes:
        vendor (str): Name used for path construction.
        product (str): Additional name used for path construction.

    """

    def __init__(self):
        self.vendor = "pypeclub"
        self.product = "openpype"
        name = "tray_publisher"
        path = appdirs.user_data_dir(self.product, self.vendor)
        super(TrayPublisherRegistry, self).__init__(name, path)


class StandaloneOverlayWidget(QtWidgets.QFrame):
    project_selected = QtCore.Signal(str)

    def __init__(self, publisher_window):
        super(StandaloneOverlayWidget, self).__init__(publisher_window)
        self.setObjectName("OverlayFrame")

        middle_frame = QtWidgets.QFrame(self)
        middle_frame.setObjectName("ChooseProjectFrame")

        content_widget = QtWidgets.QWidget(middle_frame)

        header_label = QtWidgets.QLabel("Choose project", content_widget)
        header_label.setObjectName("ChooseProjectLabel")
        # Create project models and view
        projects_model = ProjectModel()
        projects_proxy = ProjectSortFilterProxy()
        projects_proxy.setSourceModel(projects_model)
        projects_proxy.setFilterKeyColumn(0)

        projects_view = QtWidgets.QListView(content_widget)
        projects_view.setObjectName("ChooseProjectView")
        projects_view.setModel(projects_proxy)
        projects_view.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )

        confirm_btn = QtWidgets.QPushButton("Confirm", content_widget)
        cancel_btn = QtWidgets.QPushButton("Cancel", content_widget)
        cancel_btn.setVisible(False)
        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.addStretch(1)
        btns_layout.addWidget(cancel_btn, 0)
        btns_layout.addWidget(confirm_btn, 0)

        txt_filter = PlaceholderLineEdit(content_widget)
        txt_filter.setPlaceholderText("Quick filter projects..")
        txt_filter.setClearButtonEnabled(True)
        txt_filter.addAction(qtawesome.icon("fa.filter", color="gray"),
                             QtWidgets.QLineEdit.LeadingPosition)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)
        content_layout.addWidget(header_label, 0)
        content_layout.addWidget(txt_filter, 0)
        content_layout.addWidget(projects_view, 1)
        content_layout.addLayout(btns_layout, 0)

        middle_layout = QtWidgets.QHBoxLayout(middle_frame)
        middle_layout.setContentsMargins(30, 30, 10, 10)
        middle_layout.addWidget(content_widget)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addStretch(1)
        main_layout.addWidget(middle_frame, 2)
        main_layout.addStretch(1)

        projects_view.doubleClicked.connect(self._on_double_click)
        confirm_btn.clicked.connect(self._on_confirm_click)
        cancel_btn.clicked.connect(self._on_cancel_click)
        txt_filter.textChanged.connect(self._on_text_changed)

        self._projects_view = projects_view
        self._projects_model = projects_model
        self._projects_proxy = projects_proxy
        self._cancel_btn = cancel_btn
        self._confirm_btn = confirm_btn
        self._txt_filter = txt_filter

        self._publisher_window = publisher_window
        self._project_name = None

    def showEvent(self, event):
        self._projects_model.refresh()
        # Sort projects after refresh
        self._projects_proxy.sort(0)

        setting_registry = TrayPublisherRegistry()
        try:
            project_name = setting_registry.get_item("project_name")
        except ValueError:
            project_name = None

        if project_name:
            index = None
            src_index = self._projects_model.find_project(project_name)
            if src_index is not None:
                index = self._projects_proxy.mapFromSource(src_index)

            if index is not None:
                selection_model = self._projects_view.selectionModel()
                selection_model.select(
                    index,
                    QtCore.QItemSelectionModel.SelectCurrent
                )
                self._projects_view.setCurrentIndex(index)

        self._cancel_btn.setVisible(self._project_name is not None)
        super(StandaloneOverlayWidget, self).showEvent(event)

    def _on_double_click(self):
        self.set_selected_project()

    def _on_confirm_click(self):
        self.set_selected_project()

    def _on_cancel_click(self):
        self._set_project(self._project_name)

    def _on_text_changed(self):
        self._projects_proxy.setFilterRegularExpression(
            self._txt_filter.text())

    def set_selected_project(self):
        index = self._projects_view.currentIndex()

        project_name = index.data(PROJECT_NAME_ROLE)
        if project_name:
            self._set_project(project_name)

    @property
    def host(self):
        return self._publisher_window.controller.host

    def _set_project(self, project_name):
        self._project_name = project_name
        self.host.set_project_name(project_name)
        self.setVisible(False)
        self.project_selected.emit(project_name)

        setting_registry = TrayPublisherRegistry()
        setting_registry.set_item("project_name", project_name)


class TrayPublishWindow(PublisherWindow):
    def __init__(self, *args, **kwargs):
        controller = TrayPublisherController()
        super(TrayPublishWindow, self).__init__(
            controller=controller, reset_on_show=False
        )

        flags = self.windowFlags()
        # Disable always on top hint
        if flags & QtCore.Qt.WindowStaysOnTopHint:
            flags ^= QtCore.Qt.WindowStaysOnTopHint

        self.setWindowFlags(flags)

        overlay_widget = StandaloneOverlayWidget(self)

        btns_widget = self._header_extra_widget

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

        overlay_widget.project_selected.connect(self._on_project_select)
        back_to_overlay_btn.clicked.connect(self._on_back_to_overlay)
        save_btn.clicked.connect(self._on_tray_publish_save)

        self._back_to_overlay_btn = back_to_overlay_btn
        self._overlay_widget = overlay_widget

    def _set_publish_frame_visible(self, publish_frame_visible):
        super(TrayPublishWindow, self)._set_publish_frame_visible(
            publish_frame_visible
        )
        self._back_to_overlay_btn.setVisible(not publish_frame_visible)

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
        self._controller.save_changes(False)
        self._controller.reset_project_data_cache()

        self.reset()
        if not self._controller.instances:
            self._go_to_create_tab()

    def _on_tray_publish_save(self):
        self._controller.save_changes()
        print("NOT YET IMPLEMENTED")


def main():
    host = TrayPublisherHost()
    install_host(host)

    app_instance = QtWidgets.QApplication.instance()
    if app_instance is None:
        app_instance = QtWidgets.QApplication([])

    if platform.system().lower() == "windows":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            u"traypublisher"
        )

    window = TrayPublishWindow()
    window.show()
    app_instance.exec_()
