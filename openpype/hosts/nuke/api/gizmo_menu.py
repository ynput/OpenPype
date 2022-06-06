import os
import re
import nuke

from openpype.api import Logger

log = Logger.get_logger(__name__)


class GizmoMenu():
    def __init__(self, title, icon=None):

        self.toolbar = self._create_toolbar_menu(
            title,
            icon=icon
        )

        self._script_actions = []

    def _create_toolbar_menu(self, name, icon=None):
        nuke_node_menu = nuke.menu("Nodes")
        return nuke_node_menu.addMenu(
            name,
            icon=icon
        )

    def _make_menu_path(self, path, icon=None):
        parent = self.toolbar
        for folder in re.split(r"/|\\",path):
            if not folder:
                continue
            existing_menu = parent.findItem(folder)
            if existing_menu:
                parent = existing_menu
            else:
                parent = parent.addMenu(folder, icon=icon)

        return parent

    def build_from_configuration(self, configuration):
        for item in configuration:
            assert isinstance(item, dict), "Configuration is wrong!"

            # Construct parent path else parent is toolbar
            parent = self.toolbar
            gizmo_toolbar_path = item.get("gizmo_toolbar_path")
            if gizmo_toolbar_path:
                parent = self._make_menu_path(gizmo_toolbar_path)

            item_type = item.get("sourcetype")

            if item_type == ("python" or "file"):
                parent.addCommand(
                    item['title'],
                    command=str(item["command"]),
                    icon=item.get("icon"),
                    shortcut=item.get('hotkey')
                )

            # add separator
            # Special behavior for separators
            elif item_type == "separator":
                parent.addSeparator()

            # add submenu
            # items should hold a collection of submenu items (dict)
            elif item_type == "menu":
                # assert "items" in item, "Menu is missing 'items' key"
                parent.addMenu(
                    item['title'],
                    icon=item.get('icon')
                )

    def add_gizmo_path(self, gizmo_paths):
        for gizmo_path in gizmo_paths:
            if os.path.isdir(gizmo_path):
                for folder in os.listdir(gizmo_path):
                    if os.path.isdir(os.path.join(gizmo_path, folder)):
                        nuke.pluginAddPath(os.path.join(gizmo_path, folder))
                nuke.pluginAddPath(gizmo_path)
            else:
                log.warning("This path doesn't exist: {}".format(gizmo_path))
