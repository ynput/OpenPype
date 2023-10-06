import sys

from qtpy import QtWidgets, QtCore, QtGui

from openpype.tools.utils import host_tools
from openpype.style import load_stylesheet
from openpype.resources import get_openpype_icon_filepath


class OpenPypeMenu(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(OpenPypeMenu, self).__init__(*args, **kwargs)

        self.setObjectName("OpenPypeMenu")

        icon_path = get_openpype_icon_filepath()
        icon = QtGui.QIcon(icon_path)
        self.setWindowIcon(icon)

        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowStaysOnTopHint
        )

        self.setWindowTitle("OpenPype")
        workfiles_btn = QtWidgets.QPushButton("Workfiles...", self)
        create_btn = QtWidgets.QPushButton("Create...", self)
        load_btn = QtWidgets.QPushButton("Load...", self)
        publish_btn = QtWidgets.QPushButton("Publish...", self)
        inventory_btn = QtWidgets.QPushButton("Manage...", self)
        libload_btn = QtWidgets.QPushButton("Library...", self)

        # set_colorspace_btn = QtWidgets.QPushButton(
        #     "Set colorspace from presets", self
        # )
        # reset_resolution_btn = QtWidgets.QPushButton(
        #     "Set Resolution from presets", self
        # )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)

        layout.addWidget(workfiles_btn)

        layout.addSpacing(15)

        layout.addWidget(create_btn)
        layout.addWidget(load_btn)
        layout.addWidget(publish_btn)
        layout.addWidget(inventory_btn)

        layout.addSpacing(15)

        layout.addWidget(libload_btn)

        # layout.addSpacing(15)

        # layout.addWidget(set_colorspace_btn)
        # layout.addWidget(reset_resolution_btn)

        workfiles_btn.clicked.connect(self.on_workfile_clicked)
        create_btn.clicked.connect(self.on_create_clicked)
        publish_btn.clicked.connect(self.on_publish_clicked)
        load_btn.clicked.connect(self.on_load_clicked)
        inventory_btn.clicked.connect(self.on_inventory_clicked)
        libload_btn.clicked.connect(self.on_libload_clicked)

        # set_colorspace_btn.clicked.connect(self.on_set_colorspace_clicked)
        # reset_resolution_btn.clicked.connect(self.on_set_resolution_clicked)

        # Resize width, make height as small fitting as possible
        self.resize(200, 1)

    def on_workfile_clicked(self):
        print("Clicked Workfile")
        host_tools.show_workfiles()

    def on_create_clicked(self):
        print("Clicked Create")
        host_tools.show_publisher(tab="create")

    def on_publish_clicked(self):
        print("Clicked Publish")
        host_tools.show_publisher(tab="publish")

    def on_load_clicked(self):
        print("Clicked Load")
        host_tools.show_loader(use_context=True)

    def on_inventory_clicked(self):
        print("Clicked Inventory")
        host_tools.show_scene_inventory()

    def on_libload_clicked(self):
        print("Clicked Library")
        host_tools.show_library_loader()

    def on_rename_clicked(self):
        print("Clicked Rename")

    def on_set_colorspace_clicked(self):
        print("Clicked Set Colorspace")

    def on_set_resolution_clicked(self):
        print("Clicked Set Resolution")


def launch_pype_menu():
    app = QtWidgets.QApplication(sys.argv)

    pype_menu = OpenPypeMenu()

    stylesheet = load_stylesheet()
    pype_menu.setStyleSheet(stylesheet)

    pype_menu.show()

    sys.exit(app.exec_())
