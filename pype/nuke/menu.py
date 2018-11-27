import nuke
from avalon.api import Session

from pype.nuke import lib


def install():
    menubar = nuke.menu("Nuke")
    menu = menubar.findItem(Session["AVALON_LABEL"])

    menu.addSeparator()
    menu.addCommand("Set colorspace...", lib.set_colorspace)
