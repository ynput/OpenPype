import os
import nuke
from avalon.api import Session

from .lib import WorkfileSettings
from pype.api import Logger, BuildWorkfile, get_current_project_settings
from pype.tools import workfiles

log = Logger().get_logger(__name__)


def _show_workfiles(*args, **kwargs):
    workfiles.show(os.environ["AVALON_WORKDIR"])


def install():
    menubar = nuke.menu("Nuke")
    menu = menubar.findItem(Session["AVALON_LABEL"])

    # replace reset resolution from avalon core to pype's
    name = "Work Files..."
    rm_item = [
        (i, item) for i, item in enumerate(menu.items()) if name in item.name()
    ][0]

    log.debug("Changing Item: {}".format(rm_item))

    menu.removeItem(rm_item[1].name())
    menu.addCommand(
        name,
        _show_workfiles,
        index=(rm_item[0])
    )

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
        name, lambda: WorkfileSettings().set_colorspace(),
        index=(rm_item[0] + 2)
    )
    log.debug("Adding menu item: {}".format(name))

    # add workfile builder menu item
    name = "Build Workfile"
    menu.addCommand(
        name, lambda: BuildWorkfile().process(),
        index=(rm_item[0] + 7)
    )
    log.debug("Adding menu item: {}".format(name))

    # add item that applies all setting above
    name = "Apply All Settings"
    menu.addCommand(
        name,
        lambda: WorkfileSettings().set_context_settings(),
        index=(rm_item[0] + 3)
    )
    log.debug("Adding menu item: {}".format(name))

    # adding shortcuts
    add_shortcuts_from_presets()


def uninstall():

    menubar = nuke.menu("Nuke")
    menu = menubar.findItem(Session["AVALON_LABEL"])

    for item in menu.items():
        log.info("Removing menu item: {}".format(item.name()))
        menu.removeItem(item.name())


def add_shortcuts_from_presets():
    menubar = nuke.menu("Nuke")
    nuke_presets = get_current_project_settings()["nuke"]

    if nuke_presets.get("menu"):
        menu_label_mapping = {
            "manage": "Manage...",
            "create": "Create...",
            "load": "Load...",
            "build_workfile": "Build Workfile",
            "publish": "Publish..."
        }
        for menu_name, menuitems in nuke_presets.get("menu").items():
            menu = menubar.findItem(menu_name)
            for mitem_name, shortcut in menuitems.items():
                log.info("Adding Shortcut `{}` to `{}`".format(
                    shortcut, mitem_name
                ))
                try:
                    item_label = menu_label_mapping[mitem_name]
                    menuitem = menu.findItem(item_label)
                    menuitem.setShortcut(shortcut)
                except AttributeError as e:
                    log.error(e)
