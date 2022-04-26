import os
import sys

from Qt import QtWidgets, QtCore

from openpype import style
from openpype.tools.utils import host_tools

from openpype.hosts.fusion.scripts import (
    set_rendermode,
    duplicate_with_inputs
)


def load_stylesheet():
    path = os.path.join(os.path.dirname(__file__), "menu_style.qss")
    if not os.path.exists(path):
        print("Unable to load stylesheet, file not found in resources")
        return ""

    with open(path, "r") as file_stream:
        stylesheet = file_stream.read()
    return stylesheet


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
        workfiles_btn = QtWidgets.QPushButton("Workfiles...", self)
        create_btn = QtWidgets.QPushButton("Create...", self)
        publish_btn = QtWidgets.QPushButton("Publish...", self)
        load_btn = QtWidgets.QPushButton("Load...", self)
        manager_btn = QtWidgets.QPushButton("Manage...", self)
        libload_btn = QtWidgets.QPushButton("Library...", self)
        rendermode_btn = QtWidgets.QPushButton("Set render mode...", self)
        duplicate_with_inputs_btn = QtWidgets.QPushButton(
            "Duplicate with input connections", self
        )
        reset_resolution_btn = QtWidgets.QPushButton(
            "Reset Resolution from project", self
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)

        layout.addWidget(workfiles_btn)
        layout.addWidget(create_btn)
        layout.addWidget(publish_btn)
        layout.addWidget(load_btn)
        layout.addWidget(manager_btn)

        layout.addWidget(Spacer(15, self))

        layout.addWidget(libload_btn)

        layout.addWidget(Spacer(15, self))

        layout.addWidget(rendermode_btn)

        layout.addWidget(Spacer(15, self))

        layout.addWidget(duplicate_with_inputs_btn)
        layout.addWidget(reset_resolution_btn)

        self.setLayout(layout)

        workfiles_btn.clicked.connect(self.on_workfile_clicked)
        create_btn.clicked.connect(self.on_create_clicked)
        publish_btn.clicked.connect(self.on_publish_clicked)
        load_btn.clicked.connect(self.on_load_clicked)
        manager_btn.clicked.connect(self.on_manager_clicked)
        libload_btn.clicked.connect(self.on_libload_clicked)
        rendermode_btn.clicked.connect(self.on_rendernode_clicked)
        duplicate_with_inputs_btn.clicked.connect(
            self.on_duplicate_with_inputs_clicked)
        reset_resolution_btn.clicked.connect(self.on_reset_resolution_clicked)

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

    def on_rendernode_clicked(self):
        print("Clicked Set Render Mode")
        if self.render_mode_widget is None:
            window = set_rendermode.SetRenderMode()
            window.setStyleSheet(style.load_stylesheet())
            window.show()
            self.render_mode_widget = window
        else:
            self.render_mode_widget.show()

    def on_duplicate_with_inputs_clicked(self):
        duplicate_with_inputs.duplicate_with_input_connections()
        print("Clicked Set Colorspace")

    def on_reset_resolution_clicked(self):
        print("Clicked Reset Resolution")


def launch_openpype_menu():
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    pype_menu = OpenPypeMenu()

    stylesheet = load_stylesheet()
    pype_menu.setStyleSheet(stylesheet)

    pype_menu.show()

    sys.exit(app.exec_())
