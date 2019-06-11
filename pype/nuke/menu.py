import nuke
from avalon.api import Session

from pype.nuke import lib


def install():

    menubar = nuke.menu("Nuke")
    menu = menubar.findItem(Session["AVALON_LABEL"])

    # replace reset resolution from avalon core to pype's
    name = "Reset Resolution"
    new_name = "Set Resolution"
    rm_item = [
        (i, item) for i, item in enumerate(menu.items()) if name in item.name()
    ][0]
    menu.removeItem(rm_item[1].name())
    menu.addCommand(new_name, lib.reset_resolution, index=rm_item[0])

    # replace reset frame range from avalon core to pype's
    name = "Reset Frame Range"
    new_name = "Set Frame Range"
    rm_item = [
        (i, item) for i, item in enumerate(menu.items()) if name in item.name()
    ][0]
    menu.removeItem(rm_item[1].name())
    menu.addCommand(new_name, lib.reset_frame_range_handles, index=rm_item[0])

    # add colorspace menu item
    name = "Set colorspace"
    menu.addCommand(
        name, lib.set_colorspace,
        index=(rm_item[0]+2)
    )

    # add item that applies all setting above
    name = "Apply all settings"
    menu.addCommand(
        name, lib.set_context_settings, index=(rm_item[0]+3)
    )
