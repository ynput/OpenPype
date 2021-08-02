# -*- coding: utf-8 -*-
"""OpenPype script commands to be used directly in Maya."""


class ToolWindows:

    _windows = {}

    @classmethod
    def get_window(cls, tool):
        """Get widget for specific tool.

        Args:
            tool (str): Name of the tool.

        Returns:
            Stored widget.

        """
        try:
            return cls._windows[tool]
        except KeyError:
            return None

    @classmethod
    def set_window(cls, tool, window):
        """Set widget for the tool.

        Args:
            tool (str): Name of the tool.
            window (QtWidgets.QWidget): Widget

        """
        cls._windows[tool] = window


def edit_shader_definitions():
    from avalon.tools import lib
    from Qt import QtWidgets
    from openpype.hosts.maya.api.shader_definition_editor import (
        ShaderDefinitionsEditor
    )

    top_level_widgets = QtWidgets.QApplication.topLevelWidgets()
    main_window = next(widget for widget in top_level_widgets
                       if widget.objectName() == "MayaWindow")

    with lib.application():
        window = ToolWindows.get_window("shader_definition_editor")
        if not window:
            window = ShaderDefinitionsEditor(parent=main_window)
            ToolWindows.set_window("shader_definition_editor", window)
        window.show()
