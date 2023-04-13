import os
import json

import rv.qtutils
from rv.rvtypes import MinorMode
from rv.commands import isConsoleVisible, showConsole

from openpype.tools.utils import host_tools
from openpype.client import get_representations
from openpype.pipeline import (
    registered_host,
    install_host,
    discover_loader_plugins,
    load_container
)
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

    @property
    def _parent(self):
        return rv.qtutils.sessionWindow()

    def create(self, event):
        print("Launching Creator")
        host_tools.show_creator(parent=self._parent)

    def load(self, event):
        print("Launching Loader")
        host_tools.show_loader(parent=self._parent, use_context=True)

    def publish(self, event):
        print("Launching Pyblish")
        host_tools.show_publish(parent=self._parent)

    def workfiles(self, event):
        print("Launching Workfiles")
        host_tools.show_workfiles(parent=self._parent)

    def scene_inventory(self, event):
        print("Launching inventory")
        host_tools.show_scene_inventory(parent=self._parent)


def data_loader():
    incoming_data_file = os.environ.get(
        "OPENPYPE_LOADER_REPRESENTATIONS", None
    )
    if incoming_data_file:
        with open(incoming_data_file, 'rb') as file:
            decoded_data = json.load(file)
        os.remove(incoming_data_file)
        load_data(dataset=decoded_data["representations"])
    else:
        print("No data for auto-loader")


def load_data(dataset=None):

    project_name = os.environ["AVALON_PROJECT"]
    available_loaders = discover_loader_plugins(project_name)
    Loader = next(loader for loader in available_loaders
                  if loader.__name__ == "FramesLoader")

    representations = get_representations(project_name,
                                          representation_ids=dataset)

    for representation in representations:
        load_container(Loader, representation)


def createMode():
    # This function triggers for each RV session window being opened, for
    # example when using File > New Session this will trigger again. As such
    # we only want to trigger the startup install when the host is not
    # registered yet.
    if not registered_host():
        install_openpype_to_host()
        data_loader()
    return OpenPypeMenus()
