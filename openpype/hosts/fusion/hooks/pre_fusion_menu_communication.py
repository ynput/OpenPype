from openpype.lib.applications import (
    PreLaunchHook,
    LaunchTypes,
)

from openpype.hosts.fusion.api import (
    MenuSocketListener,
)


class FusionMenuCommunication(PreLaunchHook):
    """
    Prepares OpenPype Fusion socket communication.
    Takes the path of the fusion executable and
    sets up a socket for the menu communication.
    """

    app_groups = {"fusion"}
    order = 3
    launch_types = {LaunchTypes.local}

    def execute(self):
        # Connect the triggered signal to the internal function's execute slot

        menu_socket_listener = MenuSocketListener()
        menu_socket_listener.start()

        self.log.info("Starting socket listener")
