import os

from openpype.lib import get_openpype_execute_args
from openpype.lib.execute import run_detached_process
from openpype.modules import (
    click_wrap,
    OpenPypeModule,
    ITrayAction,
    IHostAddon,
)

STANDALONEPUBLISH_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class StandAlonePublishAddon(OpenPypeModule, ITrayAction, IHostAddon):
    label = "Publisher (legacy)"
    name = "standalonepublisher"
    host_name = "standalonepublisher"

    def initialize(self, modules_settings):
        self.enabled = modules_settings["standalonepublish_tool"]["enabled"]
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
        click_group.add_command(cli_main.to_click_obj())


@click_wrap.group(
    StandAlonePublishAddon.name,
    help="StandalonePublisher related commands.")
def cli_main():
    pass


@cli_main.command()
def launch():
    """Launch StandalonePublisher tool UI."""

    from openpype.tools import standalonepublish

    standalonepublish.main()
