import os
import nuke
from avalon.api import Session
from avalon.nuke.pipeline import get_main_window

from .lib import WorkfileSettings
from openpype.api import Logger, BuildWorkfile, get_current_project_settings
from openpype.tools.utils import host_tools

from avalon.nuke.pipeline import get_main_window

log = Logger().get_logger(__name__)

menu_label = os.environ["AVALON_LABEL"]


def install():
    main_window = get_main_window()
    menubar = nuke.menu("Nuke")
    menu = menubar.findItem(menu_label)

    # replace reset resolution from avalon core to pype's
    name = "Work Files..."
    rm_item = [
        (i, item) for i, item in enumerate(menu.items()) if name in item.name()
    ][0]

    log.debug("Changing Item: {}".format(rm_item))

    menu.removeItem(rm_item[1].name())
    menu.addCommand(
        name,
        lambda: host_tools.show_workfiles(parent=main_window),
        index=2
    )
    menu.addSeparator(index=3)
    # replace reset resolution from avalon core to pype's
    name = "Reset Resolution"
    new_name = "Set Resolution"
    rm_item = [
        (i, item) for i, item in enumerate(menu.items()) if name in item.name()
    ][0]

    log.debug("Changing Item: {}".format(rm_item))
    # rm_item[1].setEnabled(False)
    menu.removeItem(rm_item[1].name())
    menu.addCommand(
        new_name,
        lambda: WorkfileSettings().reset_resolution(),
        index=(rm_item[0])
    )

    # replace reset frame range from avalon core to pype's
    name = "Reset Frame Range"
    new_name = "Set Frame Range"
    rm_item = [
        (i, item) for i, item in enumerate(menu.items()) if name in item.name()
    ][0]
    log.debug("Changing Item: {}".format(rm_item))
    # rm_item[1].setEnabled(False)
    menu.removeItem(rm_item[1].name())
    menu.addCommand(
        new_name,
        lambda: WorkfileSettings().reset_frame_range_handles(),
        index=(rm_item[0])
    )

    # add colorspace menu item
    name = "Set Colorspace"
    menu.addCommand(
        name, lambda: WorkfileSettings().set_colorspace()
    )
    log.debug("Adding menu item: {}".format(name))

    # add item that applies all setting above
    name = "Apply All Settings"
    menu.addCommand(
        name,
        lambda: WorkfileSettings().set_context_settings()
    )
    log.debug("Adding menu item: {}".format(name))

    menu.addSeparator()

    # add workfile builder menu item
    name = "Build Workfile"
    menu.addCommand(
        name, lambda: BuildWorkfile().process()
    )
    log.debug("Adding menu item: {}".format(name))

    # Add experimental tools action
    menu.addSeparator()
    menu.addCommand(
        "Experimental tools...",
        lambda: host_tools.show_experimental_tools_dialog(parent=main_window)
    )

    # adding shortcuts
    add_shortcuts_from_presets()


def uninstall():

    menubar = nuke.menu("Nuke")
    menu = menubar.findItem(menu_label)

    for item in menu.items():
        log.info("Removing menu item: {}".format(item.name()))
        menu.removeItem(item.name())


def add_shortcuts_from_presets():
    menubar = nuke.menu("Nuke")
    nuke_presets = get_current_project_settings()["nuke"]["general"]

    if nuke_presets.get("menu"):
        menu_label_mapping = {
            "manage": "Manage...",
            "create": "Create...",
            "load": "Load...",
            "build_workfile": "Build Workfile",
            "publish": "Publish..."
        }

        for command_name, shortcut_str in nuke_presets.get("menu").items():
            log.info("menu_name `{}` | menu_label `{}`".format(
                command_name, menu_label
            ))
            log.info("Adding Shortcut `{}` to `{}`".format(
                shortcut_str, command_name
            ))
            try:
                menu = menubar.findItem(menu_label)
                item_label = menu_label_mapping[command_name]
                menuitem = menu.findItem(item_label)
                menuitem.setShortcut(shortcut_str)
            except AttributeError as e:
                log.error(e)
