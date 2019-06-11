import nuke
from avalon.api import Session

from pype.nuke import lib


def install():

    menubar = nuke.menu("Nuke")
    menu = menubar.findItem(Session["AVALON_LABEL"])

    # replace reset resolution and reset frame range from avalon with single
    # command that 'Reset resolution', 'Reset Frame Range' and 'Set colorspace'
    name = "Reset Resolution"
    rm_item = [
        (i, item) for i, item in enumerate(menu.items()) if name in item.name()
    ][0]
    menu.removeItem(rm_item[1].name())

    name = "Reset Frame Range"
    rm_item = [
        (i, item) for i, item in enumerate(menu.items()) if name in item.name()
    ][0]
    menu.removeItem(rm_item[1].name())

    name = "Set context settings"
    menu.addCommand(
        name, lib.set_context_settings, index=rm_item[0]
    )
