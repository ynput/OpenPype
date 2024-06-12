import os
import sys

from qtpy import QtWidgets, QtCore, QtGui

from openpype.tools.utils import host_tools
from openpype.style import load_stylesheet
from openpype.lib import register_event_callback
from openpype.hosts.fusion.scripts import (
    duplicate_with_inputs,
)
from openpype.hosts.fusion.api.lib import (
    set_asset_framerange,
    set_asset_resolution,
)
from openpype.pipeline import get_current_asset_name
from openpype.resources import get_openpype_icon_filepath
from openpype.tools.utils import get_qt_app

from .pipeline import FusionEventHandler
from .pulse import FusionPulse


MENU_LABEL = os.environ["AVALON_LABEL"]


self = sys.modules[__name__]
self.menu = None


class OpenPypeMenu(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(OpenPypeMenu, self).__init__(*args, **kwargs)

        self.setObjectName(f"{MENU_LABEL}Menu")

        icon_path = get_openpype_icon_filepath()
        icon = QtGui.QIcon(icon_path)
        self.setWindowIcon(icon)

        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.render_mode_widget = None
        self.setWindowTitle(MENU_LABEL)

        asset_label = QtWidgets.QLabel("Context", self)
        asset_label.setStyleSheet(
            """QLabel {
            font-size: 14px;
            font-weight: 600;
            color: #5f9fb8;
        }"""
        )
        asset_label.setAlignment(QtCore.Qt.AlignHCenter)

        workfiles_btn = QtWidgets.QPushButton("Workfiles...", self)
        create_btn = QtWidgets.QPushButton("Create...", self)
        load_btn = QtWidgets.QPushButton("Load...", self)
        publish_btn = QtWidgets.QPushButton("Publish...", self)
        manager_btn = QtWidgets.QPushButton("Manage...", self)
        libload_btn = QtWidgets.QPushButton("Library...", self)
        set_framerange_btn = QtWidgets.QPushButton("Set Frame Range", self)
        set_resolution_btn = QtWidgets.QPushButton("Set Resolution", self)
        duplicate_with_inputs_btn = QtWidgets.QPushButton(
            "Duplicate with input connections", self
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)

        layout.addWidget(asset_label)

        layout.addSpacing(20)

        layout.addWidget(workfiles_btn)

        layout.addSpacing(20)

        layout.addWidget(create_btn)
        layout.addWidget(load_btn)
        layout.addWidget(publish_btn)
        layout.addWidget(manager_btn)

        layout.addSpacing(20)

        layout.addWidget(libload_btn)

        layout.addSpacing(20)

        layout.addWidget(set_framerange_btn)
        layout.addWidget(set_resolution_btn)

        layout.addSpacing(20)

        layout.addWidget(duplicate_with_inputs_btn)

        self.setLayout(layout)

        # Store reference so we can update the label
        self.asset_label = asset_label

        workfiles_btn.clicked.connect(self.on_workfile_clicked)
        create_btn.clicked.connect(self.on_create_clicked)
        publish_btn.clicked.connect(self.on_publish_clicked)
        load_btn.clicked.connect(self.on_load_clicked)
        manager_btn.clicked.connect(self.on_manager_clicked)
        libload_btn.clicked.connect(self.on_libload_clicked)
        duplicate_with_inputs_btn.clicked.connect(
            self.on_duplicate_with_inputs_clicked
        )
        set_resolution_btn.clicked.connect(self.on_set_resolution_clicked)
        set_framerange_btn.clicked.connect(self.on_set_framerange_clicked)

        self._callbacks = []
        self.register_callback("taskChanged", self.on_task_changed)
        self.on_task_changed()

        # Force close current process if Fusion is closed
        self._pulse = FusionPulse(parent=self)
        self._pulse.start()

        # Detect Fusion events as OpenPype events
        self._event_handler = FusionEventHandler(parent=self)
        self._event_handler.start()

    def on_task_changed(self):
        # Update current context label
        label = get_current_asset_name()
        self.asset_label.setText(label)

    def register_callback(self, name, fn):
        # Create a wrapper callback that we only store
        # for as long as we want it to persist as callback
        def _callback(*args):
            fn()

        self._callbacks.append(_callback)
        register_event_callback(name, _callback)

    def deregister_all_callbacks(self):
        self._callbacks[:] = []

    def on_workfile_clicked(self):
        host_tools.show_workfiles()

    def on_create_clicked(self):
        host_tools.show_publisher(tab="create")

    def on_publish_clicked(self):
        host_tools.show_publisher(tab="publish")

    def on_load_clicked(self):
        host_tools.show_loader(use_context=True)

    def on_manager_clicked(self):
        host_tools.show_scene_inventory()

    def on_libload_clicked(self):
        host_tools.show_library_loader()

    def on_duplicate_with_inputs_clicked(self):
        duplicate_with_inputs.duplicate_with_input_connections()

    def on_set_resolution_clicked(self):
        set_asset_resolution()

    def on_set_framerange_clicked(self):
        set_asset_framerange()


def launch_openpype_menu():

    app = get_qt_app()

    pype_menu = OpenPypeMenu()

    stylesheet = load_stylesheet()
    pype_menu.setStyleSheet(stylesheet)

    pype_menu.show()
    self.menu = pype_menu

    result = app.exec_()
    print("Shutting down..")
    sys.exit(result)
