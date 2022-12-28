# -*- coding: utf-8 -*-
"""OpenPype startup script for Natron in GUI mode."""
from openpype.tools.utils import host_tools

import NatronGui


def get_main_window():
    # TODO: Find a way to reliably find the main window
    return None


# Menu commands to be called by Natron must be global functions in init.py
# (or must at least be available to globals?)
def openpype_show_loader():
    print("Show loader..")
    host_tools.show_loader(parent=get_main_window(),
                           use_context=True)


def openpype_show_publisher():
    host_tools.show_publisher(parent=get_main_window())


def openpype_show_scene_inventory():
    host_tools.show_scene_inventory(parent=get_main_window())


def openpype_show_library_loader():
    host_tools.show_library_loader(parent=get_main_window())


def openpype_show_workfiles():
    host_tools.show_workfiles(parent=get_main_window())


def _install_openpype_menu():
    from openpype.tools.utils import host_tools

    add_menu = NatronGui.natron.addMenuCommand

    # Add a custom menu entry with a shortcut to create our icon viewer
    add_menu("OpenPype/Load...", "openpype_show_loader()")
    add_menu("OpenPype/Publish...", "openpype_show_publisher()")
    add_menu("OpenPype/Manage...", "openpype_show_scene_inventory()")
    add_menu("OpenPype/Library...", "openpype_show_library_loader()")
    # todo: how to add a divider?
    #add_menu("OpenPype/---", "")
    add_menu("OpenPype/Work Files...", "openpype_show_workfiles()")

    def get_main_window(app):
        raise NotImplementedError("TODO")


_install_openpype_menu()
