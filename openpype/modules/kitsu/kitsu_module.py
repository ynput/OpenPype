"""Kitsu module."""

import click
import os

from openpype.modules import OpenPypeModule
from openpype_interfaces import IPluginPaths, ITrayAction


class KitsuModule(OpenPypeModule, IPluginPaths, ITrayAction):
    """Kitsu module class."""

    label = "Kitsu Connect"
    name = "kitsu"

    def initialize(self, settings):
        """Initialization of module."""
        module_settings = settings[self.name]

        # Enabled by settings
        self.enabled = module_settings.get("enabled", False)

        # Add API URL schema
        kitsu_url = module_settings["server"].strip()
        if kitsu_url:
            # Ensure web url
            if not kitsu_url.startswith("http"):
                kitsu_url = "https://" + kitsu_url

            # Check for "/api" url validity
            if not kitsu_url.endswith("api"):
                kitsu_url = "{}{}api".format(
                    kitsu_url, "" if kitsu_url.endswith("/") else "/"
                )

        self.server_url = kitsu_url

        # UI which must not be created at this time
        self._dialog = None

    def tray_init(self):
        """Tray init."""

        self._create_dialog()

    def tray_start(self):
        """Tray start."""
        from .utils.credentials import (
            load_credentials,
            validate_credentials,
            set_credentials_envs,
        )

        username, password = load_credentials()

        # Check credentials, ask them if needed
        if validate_credentials(username, password):
            set_credentials_envs(username, password)
        else:
            self.show_dialog()

    def get_global_environments(self):
        """Kitsu's global environments."""
        return {"KITSU_SERVER": self.server_url}

    def _create_dialog(self):
        # Don't recreate dialog if already exists
        if self._dialog is not None:
            return

        from .kitsu_widgets import KitsuPasswordDialog

        self._dialog = KitsuPasswordDialog()

    def show_dialog(self):
        """Show dialog to log-in."""

        # Make sure dialog is created
        self._create_dialog()

        # Show dialog
        self._dialog.open()

    def on_action_trigger(self):
        """Implementation of abstract method for `ITrayAction`."""
        self.show_dialog()

    def get_plugin_paths(self):
        """Implementation of abstract method for `IPluginPaths`."""
        current_dir = os.path.dirname(os.path.abspath(__file__))

        return {"publish": [os.path.join(current_dir, "plugins", "publish")]}

    def cli(self, click_group):
        click_group.add_command(cli_main)


@click.group(KitsuModule.name, help="Kitsu dynamic cli commands.")
def cli_main():
    pass


@cli_main.command()
@click.option("--login", envvar="KITSU_LOGIN", help="Kitsu login")
@click.option(
    "--password", envvar="KITSU_PWD", help="Password for kitsu username"
)
def push_to_zou(login: str, password: str):
    """Synchronize Zou database (Kitsu backend) with openpype database.

    Args:
        login (str): Kitsu user login
        password (str): Kitsu user password
    """
    from .utils.update_zou_with_op import sync_zou

    sync_zou(login, password)


@cli_main.command()
@click.option("-l", "--login", envvar="KITSU_LOGIN", help="Kitsu login")
@click.option(
    "-p", "--password", envvar="KITSU_PWD", help="Password for kitsu username"
)
def sync_service(login: str, password: str):
    """Synchronize openpype database from Zou sever database.

    Args:
        login (str): Kitsu user login
        password (str): Kitsu user password
    """
    from .utils.update_op_with_zou import sync_all_project
    from .utils.sync_service import start_listeners

    sync_all_project(login, password)
    start_listeners(login, password)
