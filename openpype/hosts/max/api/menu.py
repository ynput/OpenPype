# -*- coding: utf-8 -*-
"""3dsmax menu definition of OpenPype."""
from abc import ABCMeta, abstractmethod
import six
from Qt import QtWidgets, QtCore
from pymxs import runtime as rt

from openpype.tools.utils import host_tools


@six.add_metaclass(ABCMeta)
class OpenPypeMenu(object):

    def __init__(self):
        self.main_widget = self.get_main_widget()

    @staticmethod
    def get_main_widget():
        """Get 3dsmax main window."""
        return QtWidgets.QWidget.find(rt.windows.getMAXHWND())

    def get_main_menubar(self):
        """Get main Menubar by 3dsmax main window."""
        return list(self.main_widget.findChildren(QtWidgets.QMenuBar))[0]

    def get_or_create_openpype_menu(self, name="&OpenPype", before="&Help"):
        menu_bar = self.get_main_menubar()
        menu_items = menu_bar.findChildren(
            QtWidgets.QMenu, options=QtCore.Qt.FindDirectChildrenOnly)
        help_action = None
        for item in menu_items:
            if name in item.title():
                # we already have OpenPype menu
                return item

            if before in item.title():
                help_action = item.menuAction()

        op_menu = QtWidgets.QMenu("&OpenPype")
        menu_bar.insertMenu(before, op_menu)
        return op_menu

    def build_openpype_menu(self):
        openpype_menu = self.get_or_create_openpype_menu()
        load_action = QtWidgets.QAction("Load...", openpype_menu)
        load_action.triggered.connect(self.load_callback)
        openpype_menu.addAction(load_action)

        publish_action = QtWidgets.QAction("Publish...", openpype_menu)
        publish_action.triggered.connect(self.publish_callback)
        openpype_menu.addAction(publish_action)

        manage_action = QtWidgets.QAction("Manage...", openpype_menu)
        manage_action.triggered.connect(self.manage_callback)
        openpype_menu.addAction(manage_action)

        library_action = QtWidgets.QAction("Library...", openpype_menu)
        library_action.triggered.connect(self.library_callback)
        openpype_menu.addAction(library_action)

        openpype_menu.addSeparator()

        workfiles_action = QtWidgets.QAction("Work Files...", openpype_menu)
        workfiles_action.triggered.connect(self.workfiles_callback)
        openpype_menu.addAction(workfiles_action)

    def load_callback(self):
        host_tools.show_loader(parent=self.main_widget)

    def publish_callback(self):
        host_tools.show_publisher(parent=self.main_widget)

    def manage_callback(self):
        host_tools.show_subset_manager(parent=self.main_widget)

    def library_callback(self):
        host_tools.show_library_loader(parent=self.main_widget)

    def workfiles_callback(self):
        host_tools.show_workfiles(parent=self.main_widget)
