import os
import json

from rv.rvtypes import MinorMode
from rv.commands import isConsoleVisible, showConsole

from openpype.tools.utils import host_tools

from openpype.pipeline import install_host
from openpype.hosts.openrv.api import OpenRVHost


def install_openpype_to_host():
    host = OpenRVHost()
    install_host(host)


class OpenPypeMenus(MinorMode):

    def __init__(self):
        MinorMode.__init__(self)
        self.init(
            name="py-openpype",
            globalBindings=None,
            overrideBindings=None,
            menu=[
                # Menu name
                # NOTE: If it already exists it will merge with existing
                # and add submenus / menuitems to the existing one
                ("OpenPype", [
                    # Menuitem name, actionHook (event), key, stateHook
                    ("Create...", self.create, None, None),
                    ("Load...", self.load, None, None),
                    ("Publish...", self.publish, None, None),
                    ("Manage...", self.scene_inventory, None, None),
                    # TODO: add separator if possible
                    ("Work Files...", self.workfiles, None, None),
                ])
            ]
        )
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

    def scene_inventory(self, event):
        print("Launching inventory")
        host_tools.show_scene_inventory()


def data_loader():
    incoming_data_file = os.environ.get("OPENPYPE_LOADER_REPRESENTATIONS",
                                        None)
    if incoming_data_file:
        with open(incoming_data_file, 'rb') as pypefile:
            decoded_data = json.load(pypefile)
        os.remove(incoming_data_file)
        load_data(dataset=decoded_data["representations"])
    else:
        print("No data for auto-loader")


def load_data(dataset=None):
    from openpype.pipeline.load import discover_loader_plugins
    from openpype.pipeline import load_container
    from openpype.client import get_representations

    project_name = os.environ["AVALON_PROJECT"]
    available_loaders = discover_loader_plugins(project_name)
    Loader = next(loader for loader in available_loaders
                  if loader.__name__ == "FramesLoader")

    representations = get_representations(project_name,
                                          representation_ids=dataset)

    for representation in representations:
        container = load_container(Loader, representation)


def createMode():
    install_openpype_to_host()
    data_loader()
    return OpenPypeMenus()
