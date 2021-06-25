# -*- coding: utf-8 -*-
"""OpenPype script commands to be used directly in Maya."""
import sys


def edit_shader_definitions():
    from avalon.tools import lib
    from Qt import QtWidgets
    from openpype.hosts.maya.api.shader_definition_editor import (
        ShaderDefinitionsEditor
    )

    module = sys.modules[__name__]
    module.window = None

    top_level_widgets = QtWidgets.QApplication.topLevelWidgets()
    main_window = next(widget for widget in top_level_widgets
                       if widget.objectName() == "MayaWindow")

    with lib.application():
        window = ShaderDefinitionsEditor(parent=main_window)
        window.show()

        module.window = window
