# -*- coding: utf-8 -*-
"""OpenPype script commands to be used directly in Maya."""
import sys


def edit_shader_definitions():
    from avalon.tools import lib
    from Qt import QtWidgets, QtCore
    from openpype.hosts.maya.api.shader_definition_editor import ShaderDefinitionsEditor

    print("Editing shader definitions...")

    module = sys.modules[__name__]
    module.window = None

    top_level_widgets = QtWidgets.QApplication.topLevelWidgets()
    mainwindow = next(widget for widget in top_level_widgets
                      if widget.objectName() == "MayaWindow")

    with lib.application():
        window = ShaderDefinitionsEditor(parent=mainwindow)
        # window.setStyleSheet(style.load_stylesheet())
        window.show()

        module.window = window
