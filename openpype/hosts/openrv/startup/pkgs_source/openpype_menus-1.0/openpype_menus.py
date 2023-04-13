from rv.rvtypes import *
from rv.commands import *
from rv.extra_commands import *

from openpype.tools.utils import host_tools

from openpype.pipeline import install_host
from openpype.hosts.openrv.api import OpenRVHost


def install_openpype_to_host():
    host = OpenRVHost()
    install_host(host)


class OpenPypeMenus(MinorMode):

    def __init__(self):
        MinorMode.__init__(self)
        self.init("py-openpype", None, None, [
            # Menu name
            # NOTE: If it already exists it will merge with existing
            # and add submenus / menuitems to the existing one
            ("-= OpenPype =-", [
                # Menuitem name, actionHook (event), key, stateHook
                ("Workfiles", self.workfiles, None, None),
                ("Create", self.create, None, None),
                ("Load", self.load, None, None),
                ("Publish", self.publish, None, None)
            ])
        ])
        if not isConsoleVisible():
            showConsole()

    def create(self, event):
        print("Launching Creator")
        host_tools.show_creator()

    def load(self, event):
        print("Launching Loader")
        host_tools.show_loader(parent=[], use_context=True)

    def publish(self, event):
        print("Launching Pyblish")
        host_tools.show_publish()

    def workfiles(self, event):
        print("Launching Workfiles")
        host_tools.show_workfiles()


def createMode():
    install_openpype_to_host()
    return OpenPypeMenus()
