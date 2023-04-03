# -*- coding: utf-8 -*-
"""OpenPype script commands to be used directly in Maya."""
from maya import cmds

from openpype.client import get_asset_by_name, get_project
from openpype.pipeline import legacy_io


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
    from qtpy import QtWidgets
    from openpype.hosts.maya.api.shader_definition_editor import (
        ShaderDefinitionsEditor
    )
    from openpype.tools.utils import qt_app_context

    top_level_widgets = QtWidgets.QApplication.topLevelWidgets()
    main_window = next(widget for widget in top_level_widgets
                       if widget.objectName() == "MayaWindow")

    with qt_app_context():
        window = ToolWindows.get_window("shader_definition_editor")
        if not window:
            window = ShaderDefinitionsEditor(parent=main_window)
            ToolWindows.set_window("shader_definition_editor", window)
        window.show()


def _resolution_from_document(doc):
    if not doc or "data" not in doc:
        print("Entered document is not valid. \"{}\"".format(str(doc)))
        return None

    resolution_width = doc["data"].get("resolutionWidth")
    resolution_height = doc["data"].get("resolutionHeight")
    # Backwards compatibility
    if resolution_width is None or resolution_height is None:
        resolution_width = doc["data"].get("resolution_width")
        resolution_height = doc["data"].get("resolution_height")

    # Make sure both width and height are set
    if resolution_width is None or resolution_height is None:
        cmds.warning(
            "No resolution information found for \"{}\"".format(doc["name"])
        )
        return None

    return int(resolution_width), int(resolution_height)


def reset_resolution():
    # Default values
    resolution_width = 1920
    resolution_height = 1080

    # Get resolution from asset
    project_name = legacy_io.active_project()
    asset_name = legacy_io.Session["AVALON_ASSET"]
    asset_doc = get_asset_by_name(project_name, asset_name)
    resolution = _resolution_from_document(asset_doc)
    # Try get resolution from project
    if resolution is None:
        # TODO go through visualParents
        print((
            "Asset \"{}\" does not have set resolution."
            " Trying to get resolution from project"
        ).format(asset_name))
        project_doc = get_project(project_name)
        resolution = _resolution_from_document(project_doc)

    if resolution is None:
        msg = "Using default resolution {}x{}"
    else:
        resolution_width, resolution_height = resolution
        msg = "Setting resolution to {}x{}"

    print(msg.format(resolution_width, resolution_height))

    # set for different renderers
    # arnold, vray, redshift, renderman

    renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer").lower()
    # handle various renderman names
    if renderer.startswith("renderman"):
        renderer = "renderman"

    # default attributes are usable for Arnold, Renderman and Redshift
    width_attr_name = "defaultResolution.width"
    height_attr_name = "defaultResolution.height"

    # Vray has its own way
    if renderer == "vray":
        width_attr_name = "vraySettings.width"
        height_attr_name = "vraySettings.height"

    cmds.setAttr(width_attr_name, resolution_width)
    cmds.setAttr(height_attr_name, resolution_height)
