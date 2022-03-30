import sys

from Qt import QtWidgets, QtCore

from avalon import api
from openpype.tools.utils import host_tools

from openpype.style import load_stylesheet
from openpype.lib import register_event_callback
from openpype.hosts.fusion.scripts import (
    set_rendermode,
    duplicate_with_inputs
)
from openpype.hosts.fusion.api import (
    set_framerange
)


class Spacer(QtWidgets.QWidget):
    def __init__(self, height, *args, **kwargs):
        super(Spacer, self).__init__(*args, **kwargs)

        self.setFixedHeight(height)

        real_spacer = QtWidgets.QWidget(self)
        real_spacer.setObjectName("Spacer")
        real_spacer.setFixedHeight(height)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(real_spacer)

        self.setLayout(layout)


class OpenPypeMenu(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(OpenPypeMenu, self).__init__(*args, **kwargs)

        self.setObjectName("OpenPypeMenu")

        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.render_mode_widget = None
        self.setWindowTitle("OpenPype")

        asset_label = QtWidgets.QLabel("Context", self)
        asset_label.setStyleSheet("""QLabel {
            font-size: 14px;
            font-weight: 600;
            color: #5f9fb8;
        }""")
        asset_label.setAlignment(QtCore.Qt.AlignHCenter)

        workfiles_btn = QtWidgets.QPushButton("Workfiles...", self)
        create_btn = QtWidgets.QPushButton("Create...", self)
        publish_btn = QtWidgets.QPushButton("Publish...", self)
        load_btn = QtWidgets.QPushButton("Load...", self)
        manager_btn = QtWidgets.QPushButton("Manage...", self)
        libload_btn = QtWidgets.QPushButton("Library...", self)
        rendermode_btn = QtWidgets.QPushButton("Set render mode...", self)
        set_framerange_btn = QtWidgets.QPushButton("Set Frame Range", self)
        set_resolution_btn = QtWidgets.QPushButton("Set Resolution", self)
        duplicate_with_inputs_btn = QtWidgets.QPushButton(
            "Duplicate with input connections", self
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)

        layout.addWidget(asset_label)

        layout.addWidget(Spacer(15, self))

        layout.addWidget(workfiles_btn)

        layout.addWidget(Spacer(15, self))

        layout.addWidget(create_btn)
        layout.addWidget(load_btn)
        layout.addWidget(publish_btn)
        layout.addWidget(manager_btn)

        layout.addWidget(Spacer(15, self))

        layout.addWidget(libload_btn)

        layout.addWidget(Spacer(15, self))

        layout.addWidget(set_framerange_btn)
        layout.addWidget(set_resolution_btn)
        layout.addWidget(rendermode_btn)

        layout.addWidget(Spacer(15, self))

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
        rendermode_btn.clicked.connect(self.on_rendermode_clicked)
        duplicate_with_inputs_btn.clicked.connect(
            self.on_duplicate_with_inputs_clicked)
        set_resolution_btn.clicked.connect(self.on_set_resolution_clicked)
        set_framerange_btn.clicked.connect(self.on_set_framerange_clicked)

        self._callbacks = []
        self.register_callback("taskChanged", self.on_task_changed)
        self.on_task_changed()

    def on_task_changed(self):
        # Update current context label
        label = api.Session["AVALON_ASSET"]
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
        print("Clicked Workfile")
        host_tools.show_workfiles()

    def on_create_clicked(self):
        print("Clicked Create")
        host_tools.show_creator()

    def on_publish_clicked(self):
        print("Clicked Publish")
        host_tools.show_publish()

    def on_load_clicked(self):
        print("Clicked Load")
        host_tools.show_loader(use_context=True)

    def on_manager_clicked(self):
        print("Clicked Manager")
        host_tools.show_scene_inventory()

    def on_libload_clicked(self):
        print("Clicked Library")
        host_tools.show_library_loader()

    def on_rendermode_clicked(self):
        print("Clicked Set Render Mode")
        if self.render_mode_widget is None:
            window = set_rendermode.SetRenderMode()
            window.setStyleSheet(load_stylesheet())
            window.show()
            self.render_mode_widget = window
        else:
            self.render_mode_widget.show()

    def on_duplicate_with_inputs_clicked(self):
        print("Clicked Duplicate with input connections")
        duplicate_with_inputs.duplicate_with_input_connections()

    def on_set_resolution_clicked(self):
        print("Clicked Reset Resolution")

    def on_set_framerange_clicked(self):
        print("Clicked Reset Framerange")
        set_framerange()


def launch_openpype_menu():
    app = QtWidgets.QApplication(sys.argv)

    pype_menu = OpenPypeMenu()

    stylesheet = load_stylesheet()
    pype_menu.setStyleSheet(stylesheet)

    pype_menu.show()

    result = app.exec_()
    print("Shutting down..")
    sys.exit(result)
