import click
import os

VERSION_CONTROL_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

from .. import OpenPypeModule
from ..interfaces import ITrayService

_typing = False
if _typing:
    from typing import Any
del _typing


class VersionControlModule(OpenPypeModule, ITrayService):
    # _icon_name = "mdi.jira"
    # _icon_scale = 1.3

    # Properties:
    @property
    def name(self):
        # type: () -> str
        return "version_control"

    @property
    def label(self):
        # type: () -> str
        return f"Version Control: {self.active_version_control_system.title()}"

    # Public Methods:
    def initialize(self, settings):
        # type: (dict[str, Any]) -> None
        assert self.name in settings, (
            "{} not found in settings - make sure they are defined in the defaults".format(self.name)
        )
        vc_settings = settings[self.name]  #  type: dict[str, Any]
        enabled = vc_settings["enabled"]  # type: bool
        active_version_control_system = vc_settings["active_version_control_system"]  # type: str
        self.active_version_control_system = active_version_control_system
        self.set_service_running_icon() if enabled else self.set_service_failed_icon()
        self.enabled = enabled

    def get_global_environments(self):
        # return {"ACTIVE_VERSION_CONTROL_SYSTEM": self.active_version_control_system}
        return {}

    def tray_exit(self):
        return

    def tray_init(self):
        return

    def tray_start(self):
        return

    def cli(self, click_group):
        click_group.add_command(cli_main)


@click.group("version_control", help="Version Control module related commands.")
def cli_main():
    pass
