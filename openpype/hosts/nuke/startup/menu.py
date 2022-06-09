import nuke
import os

from openpype.api import Logger
from openpype.pipeline import install_host
from openpype.hosts.nuke import api
from openpype.hosts.nuke.api.lib import (
    on_script_load,
    check_inventory_versions,
    WorkfileSettings,
    dirmap_file_name_filter,
    add_scripts_gizmo
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


add_scripts_menu()

add_scripts_gizmo()
