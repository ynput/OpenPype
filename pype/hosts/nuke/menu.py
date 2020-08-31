import nuke
from avalon.api import Session

from pype.hosts.nuke import lib
from ...lib import BuildWorkfile
from pype.api import Logger

log = Logger().get_logger(__name__, "nuke")


def install():
    menubar = nuke.menu("Nuke")
    menu = menubar.findItem(Session["AVALON_LABEL"])
    workfile_settings = lib.WorkfileSettings
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
        lambda: workfile_settings().reset_resolution(),
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
        lambda: workfile_settings().reset_frame_range_handles(),
        index=(rm_item[0])
    )

    # add colorspace menu item
    name = "Set Colorspace"
    menu.addCommand(
        name, lambda: workfile_settings().set_colorspace(),
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
        lambda: workfile_settings().set_context_settings(),
        index=(rm_item[0] + 3)
    )
    log.debug("Adding menu item: {}".format(name))


def uninstall():

    menubar = nuke.menu("Nuke")
    menu = menubar.findItem(Session["AVALON_LABEL"])

    for item in menu.items():
        log.info("Removing menu item: {}".format(item.name()))
        menu.removeItem(item.name())
