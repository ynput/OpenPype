import os

import click

from openpype.lib import get_openpype_execute_args
from openpype.lib.execute import run_detached_process
from openpype.modules import OpenPypeModule
from openpype.modules.interfaces import ITrayAction, IHostModule

STANDALONEPUBLISH_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class StandAlonePublishModule(OpenPypeModule, ITrayAction, IHostModule):
    label = "Publish"
    name = "standalonepublish_tool"
    host_name = "standalonepublisher"

    def initialize(self, modules_settings):
        self.enabled = modules_settings[self.name]["enabled"]
        self.publish_paths = [
            os.path.join(STANDALONEPUBLISH_ROOT_DIR, "plugins", "publish")
        ]

    def tray_init(self):
        return

    def on_action_trigger(self):
        self.run_standalone_publisher()

    def connect_with_modules(self, enabled_modules):
        """Collect publish paths from other modules."""

        publish_paths = self.manager.collect_plugin_paths()["publish"]
        self.publish_paths.extend(publish_paths)

    def run_standalone_publisher(self):
        args = get_openpype_execute_args("module", self.name, "launch")
        run_detached_process(args)

    def cli(self, click_group):
        click_group.add_command(cli_main)


@click.group(
    StandAlonePublishModule.name,
    help="StandalonePublisher related commands.")
def cli_main():
    pass


@cli_main.command()
def launch():
    """Launch StandalonePublisher tool UI."""

    from openpype.tools import standalonepublish

    standalonepublish.main()
