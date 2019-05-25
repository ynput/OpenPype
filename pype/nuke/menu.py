import nuke
from avalon.api import Session

from pype.nuke import lib


def install():

    menubar = nuke.menu("Nuke")
    menu = menubar.findItem(Session["AVALON_LABEL"])

    # replace reset resolution from avalon core to pype's
    name = "Reset Resolution"
    rm_item = [(i, item)
               for i, item in enumerate(menu.items())
               if name in item.name()][0]
    menu.removeItem(rm_item[1].name())
    menu.addCommand(rm_item[1].name(), lib.reset_resolution, index=rm_item[0])

    # replace reset resolution from avalon core to pype's
    name = "Reset Frame Range"
    rm_item = [(i, item)
               for i, item in enumerate(menu.items())
               if name in item.name()][0]
    menu.removeItem(rm_item[1].name())
    menu.addCommand(
        rm_item[1].name(),
        lib.reset_frame_range_handles,
        index=rm_item[0])

    # add colorspace menu item
    menu.addCommand("Set colorspace...", lib.set_colorspace,
                    index=rm_item[0] + 1)
