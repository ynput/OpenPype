import os
import logging
import nuke

log = logging.getLogger(__name__)


class GizmoMenu():
    def __init__(self, *args, **kwargs):
        self._script_actions = []

    def build_from_configuration(self, parent, configuration):
        for item in configuration:
            assert isinstance(item, dict), "Configuration is wrong!"

            # skip items which have no `type` key
            item_type = item.get('type', None)
            if not item_type:
                log.warning("Missing 'type' from configuration item")
                continue

            if item_type == "action":
                # filter out `type` from the item dict
                config = {key: value for key, value in
                          item.items() if key != "type"}

                command = str(config['command'])

                if command.find('{pipe_path}') > -1:
                    command = command.format(
                        pipe_path=os.environ['QUAD_PLUGIN_PATH']
                    )

                icon = config.get('icon', None)
                if icon:
                    try:
                        icon = icon.format(**os.environ)
                    except KeyError as e:
                        log.warning("This environment variable doesn't exist: "
                                    "{}".format(e))

                hotkey = config.get('hotkey', None)

                parent.addCommand(
                    config['title'],
                    command=command,
                    icon=icon,
                    shortcut=hotkey
                )

            # add separator
            # Special behavior for separators
            if item_type == "separator":
                parent.addSeparator()

            # add submenu
            # items should hold a collection of submenu items (dict)
            elif item_type == "menu":
                assert "items" in item, "Menu is missing 'items' key"

                icon = item.get('icon', None)
                if icon:
                    try:
                        icon = icon.format(**os.environ)
                    except KeyError as e:
                        log.warning("This environment variable doesn't exist: "
                                    "{}".format(e))
                menu = parent.addMenu(item['title'], icon=icon)
                self.build_from_configuration(menu, item["items"])

    def add_gizmo_path(self, gizmo_paths):
        for gizmo_path in gizmo_paths:
            if os.path.isdir(gizmo_path):
                for folder in os.listdir(gizmo_path):
                    if os.path.isdir(os.path.join(gizmo_path, folder)):
                        nuke.pluginAddPath(os.path.join(gizmo_path, folder))
                nuke.pluginAddPath(gizmo_path)
            else:
                log.warning("This path doesn't exist: {}".format(gizmo_path))
