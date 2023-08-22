import socket
import json
import click
from qtpy import QtCore
from openpype.lib import Logger
from openpype.pipeline import (
    install_host,
    registered_host,
)
from openpype.tools.utils import host_tools
from openpype.hosts.fusion.api import (
    set_asset_framerange,
    set_asset_resolution,
    FusionHost,
)
from openpype.hosts.fusion.scripts import (
    duplicate_with_inputs,
)
from openpype.modules import OpenPypeModule, IHostAddon

log = Logger.get_logger(__name__)


class FusionMenuListener(OpenPypeModule, IHostAddon):
    name = "fusionmenulistener"
    host_name = "fusionmenulistener"

    def initialize(self, modules_settings):
        self.enabled = True

    def cli(self, click_group):
        click_group.add_command(cli_main)


@click.group(
    FusionMenuListener.name, help="FusionMenuListener related commands."
)
def cli_main():
    pass


@cli_main.command()
def launch():
    """Launch Fusion Menu listener."""
    listener = MenuSocketListener()
    listener.run()


class MenuSocketListener(QtCore.QThread):
    def __init__(self, parent=None):
        super(MenuSocketListener, self).__init__(parent=parent)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        install_host(FusionHost())
        log.info(f"Registered host: {registered_host()}")
        log.info(
            f"get_current_project_name: "
            f"{registered_host().get_current_project_name()}"
        )

        self.tools_helper = host_tools.HostToolsHelper()

    def run(self):
        # if not is_socket_open("localhost", 12345):
        #    self.log.info("Socket already in use")

        self.server_socket.bind(
            ("localhost", 12345)
        )  # Use 0 for a dynamic port
        self.server_socket.listen(1)

        print(
            "self.server_socket.getsockname(): ",
            self.server_socket.getsockname(),
        )

        while True:
            connection, client_address = self.server_socket.accept()
            json_data = connection.recv(
                1024
            ).decode()  # Receive and decode the data
            if json_data:
                data = json.loads(json_data)  # Deserialize JSON to dictionary
                self.execute(data)
            connection.close()

    def execute(self, data):
        fusion_uuid = data.get("uuid")
        log.info(f"FusionID: {fusion_uuid}")

        if data["menu_item"] == "workfiles":
            self.tools_helper.show_workfiles()
        elif data["menu_item"] == "create":
            self.tools_helper.show_creator()
        elif data["menu_item"] == "load":
            self.tools_helper.show_loader(use_context=True)
        elif data["menu_item"] == "publish":
            self.tools_helper.show_publish()
        elif data["menu_item"] == "manage":
            self.tools_helper.show_scene_inventory()
        elif data["menu_item"] == "library":
            self.tools_helper.show_library_loader()
        elif data["menu_item"] == "set_frame_range":
            set_asset_framerange()
        elif data["menu_item"] == "set_resolution":
            set_asset_resolution()
        elif data["menu_item"] == "duplicate_with_input_connections":
            duplicate_with_inputs.duplicate_with_input_connections()
