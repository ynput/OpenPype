import nuke
import os

from openpype.api import Logger
from openpype.settings import get_project_settings
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


add_scripts_menu()


def add_scripts_gizmo():
    try:
        from openpype.hosts.nuke.api import lib
    except ImportError:
        log.warning(
            "Skipping studio.gizmo install, because "
            "'scriptsgizmo' module seems unavailable."
        )
        return

    for gizmo in project_settings["nuke"]["gizmo"]:
        config = gizmo["gizmo_definition"]
        toolbar_name = gizmo["toolbar_menu_name"]
        gizmo_path = gizmo["gizmo_path"]
        icon = gizmo['toolbar_icon_path']

        if not any(gizmo_path):
            log.warning("Skipping studio gizmo, no gizmo path found.")
            return

        if not config:
            log.warning("Skipping studio gizmo, no definition found.")
            return

        try:
            icon = icon.format(**os.environ)
        except KeyError as e:
            log.warning(f"This environment variable doesn't exist: {e}")

        for gizmo in gizmo_path:
            try:
                gizmo = gizmo.format(**os.environ)
                gizmo_path.append(gizmo)
                gizmo_path.pop(0)
            except KeyError as e:
                log.warning(f"This environment variable doesn't exist: {e}")

        nuke_toolbar = nuke.menu("Nodes")
        toolbar = nuke_toolbar.addMenu(toolbar_name, icon=icon)

        # run the launcher for Nuke toolbar
        studio_menu = lib.gizmo_creation(
            title=toolbar_name,
            parent=toolbar,
            objectName=toolbar_name.lower().replace(" ", "_"),
            icon=icon
        )

        # apply configuration
        studio_menu.add_gizmo_path(gizmo_path)
        studio_menu.build_from_configuration(toolbar, config)


add_scripts_gizmo()
