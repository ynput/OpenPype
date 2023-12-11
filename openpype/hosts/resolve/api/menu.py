import os
import sys

from qtpy import QtWidgets, QtCore, QtGui

from openpype.tools.utils import host_tools
from openpype.pipeline import registered_host


MENU_LABEL = os.environ["AVALON_LABEL"]


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

        self.setObjectName(f"{MENU_LABEL}Menu")

        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowStaysOnTopHint
        )

        self.setWindowTitle(f"{MENU_LABEL}")
        save_current_btn = QtWidgets.QPushButton("Save current file", self)
        workfiles_btn = QtWidgets.QPushButton("Workfiles ...", self)
        create_btn = QtWidgets.QPushButton("Create ...", self)
        publish_btn = QtWidgets.QPushButton("Publish ...", self)
        load_btn = QtWidgets.QPushButton("Load ...", self)
        inventory_btn = QtWidgets.QPushButton("Manager ...", self)
        subsetm_btn = QtWidgets.QPushButton("Subset Manager ...", self)
        libload_btn = QtWidgets.QPushButton("Library ...", self)
        experimental_btn = QtWidgets.QPushButton(
            "Experimental tools ...", self
        )
        # rename_btn = QtWidgets.QPushButton("Rename", self)
        # set_colorspace_btn = QtWidgets.QPushButton(
        #     "Set colorspace from presets", self
        # )
        # reset_resolution_btn = QtWidgets.QPushButton(
        #     "Set Resolution from presets", self
        # )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)

        layout.addWidget(save_current_btn)

        layout.addWidget(Spacer(15, self))

        layout.addWidget(workfiles_btn)
        layout.addWidget(create_btn)
        layout.addWidget(publish_btn)
        layout.addWidget(load_btn)
        layout.addWidget(inventory_btn)
        layout.addWidget(subsetm_btn)

        layout.addWidget(Spacer(15, self))

        layout.addWidget(libload_btn)

        # layout.addWidget(Spacer(15, self))

        # layout.addWidget(rename_btn)

        # layout.addWidget(Spacer(15, self))

        # layout.addWidget(set_colorspace_btn)
        # layout.addWidget(reset_resolution_btn)
        layout.addWidget(Spacer(15, self))
        layout.addWidget(experimental_btn)

        self.setLayout(layout)

        save_current_btn.clicked.connect(self.on_save_current_clicked)
        save_current_btn.setShortcut(QtGui.QKeySequence.Save)
        workfiles_btn.clicked.connect(self.on_workfile_clicked)
        create_btn.clicked.connect(self.on_create_clicked)
        publish_btn.clicked.connect(self.on_publish_clicked)
        load_btn.clicked.connect(self.on_load_clicked)
        inventory_btn.clicked.connect(self.on_inventory_clicked)
        subsetm_btn.clicked.connect(self.on_subsetm_clicked)
        libload_btn.clicked.connect(self.on_libload_clicked)
        # rename_btn.clicked.connect(self.on_rename_clicked)
        # set_colorspace_btn.clicked.connect(self.on_set_colorspace_clicked)
        # reset_resolution_btn.clicked.connect(self.on_set_resolution_clicked)
        experimental_btn.clicked.connect(self.on_experimental_clicked)

    def on_save_current_clicked(self):
        host = registered_host()
        current_file = host.get_current_workfile()
        if not current_file:
            print("Current project is not saved. "
                  "Please save once first via workfiles tool.")
            host_tools.show_workfiles()
            return

        print(f"Saving current file to: {current_file}")
        host.save_workfile(current_file)

    def on_workfile_clicked(self):
        print("Clicked Workfile")
        host_tools.show_workfiles()

    def on_create_clicked(self):
        print("Clicked Create")
        host_tools.show_creator()

    def on_publish_clicked(self):
        print("Clicked Publish")
        host_tools.show_publish(parent=None)

    def on_load_clicked(self):
        print("Clicked Load")
        host_tools.show_loader(use_context=True)

    def on_inventory_clicked(self):
        print("Clicked Inventory")
        host_tools.show_scene_inventory()

    def on_subsetm_clicked(self):
        print("Clicked Subset Manager")
        host_tools.show_subset_manager()

    def on_libload_clicked(self):
        print("Clicked Library")
        host_tools.show_library_loader()

    def on_rename_clicked(self):
        print("Clicked Rename")

    def on_set_colorspace_clicked(self):
        print("Clicked Set Colorspace")

    def on_set_resolution_clicked(self):
        print("Clicked Set Resolution")

    def on_experimental_clicked(self):
        host_tools.show_experimental_tools_dialog()


def launch_pype_menu():
    app = QtWidgets.QApplication(sys.argv)

    pype_menu = OpenPypeMenu()

    stylesheet = load_stylesheet()
    pype_menu.setStyleSheet(stylesheet)

    pype_menu.show()

    sys.exit(app.exec_())
