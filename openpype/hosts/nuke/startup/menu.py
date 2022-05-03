import nuke
import os
import json

import avalon.api
from openpype.api import Logger
from openpype.pipeline import install_host
from openpype.hosts.nuke import api
from openpype.hosts.nuke.api.lib import (
    on_script_load,
    check_inventory_versions,
    WorkfileSettings,
    dirmap_file_name_filter
)
from openpype.settings import get_project_settings

log = Logger.get_logger(__name__)


install_host(api)

# fix ffmpeg settings on script
nuke.addOnScriptLoad(on_script_load)

# set checker for last versions on loaded containers
nuke.addOnScriptLoad(check_inventory_versions)
nuke.addOnScriptSave(check_inventory_versions)

# # set apply all workfile settings on script load and save
nuke.addOnScriptLoad(WorkfileSettings().set_context_settings)

nuke.addFilenameFilter(dirmap_file_name_filter)

log.info('Automatic syncing of write file knob to script version')


def add_scripts_menu():
    try:
        from scriptsmenu import launchfornuke
    except ImportError:
        log.warning(
            "Skipping studio.menu install, because "
            "'scriptsmenu' module seems unavailable."
        )
        return

    # load configuration of custom menu
    project_settings = get_project_settings(os.getenv("AVALON_PROJECT"))
    config = project_settings["nuke"]["scriptsmenu"]["definition"]
    _menu = project_settings["nuke"]["scriptsmenu"]["name"]

    if not config:
        log.warning("Skipping studio menu, no definition found.")
        return

    # run the launcher for Maya menu
    studio_menu = launchfornuke.main(title=_menu.title())

    # apply configuration
    studio_menu.build_from_configuration(studio_menu, config)


def add_gizmos():
    """ Build a custom gizmo menu from a yaml description file.
    """
    quad_plugin_path = os.environ.get("QUAD_PLUGIN_PATH")
    gizmos_folder = os.path.join(quad_plugin_path, 'nuke/gizmos')
    icons_folder = os.path.join(quad_plugin_path, 'nuke/icons')
    json_file = os.path.join(quad_plugin_path, 'nuke/toolbar.json')

    if os.path.isdir(gizmos_folder):
        for p in os.listdir(gizmos_folder):
            if os.path.isdir(os.path.join(gizmos_folder, p)):
                nuke.pluginAddPath(os.path.join(gizmos_folder, p))
        nuke.pluginAddPath(gizmos_folder)

    with open(json_file, 'rb') as fd:
        try:
            data = json.loads(fd.read())
        except Exception as e:
            print(f"Problem occurs when reading toolbar file: {e}")
            return

        if data is None or not isinstance(data, list):
            # return early if the json file is empty or not well structured
            return

        bar = nuke.menu("Nodes")
        menu = bar.addMenu(
            "FixStudio",
            icon=os.path.join(icons_folder, 'fixstudio.png')
        )

        # populate the menu
        for entry in data:
            # make fail if the name or command key doesn't exists
            name = entry['name']

            command = entry.get('command', "")

            if command.find('{pipe_path}') > -1:
                command = command.format(pipe_path=os.environ['QUAD_PLUGIN_PATH'])

            hotkey = entry.get('hotkey', "")
            icon = entry.get('icon', "")

            parent_name = os.path.dirname(name)

            if 'separator' in name:
                current = menu.findItem(parent_name)
                if current:
                    current.addSeparator()
            else:
                menu.addCommand(
                    name, command=command, shortcut=hotkey, icon=icon,
                )


add_gizmos()
add_scripts_menu()
