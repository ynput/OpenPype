import os

import click

from openpype.lib import get_openpype_execute_args
from openpype.lib.execute import run_detached_process
from openpype.modules import OpenPypeModule
from openpype.modules.interfaces import ITrayAction, IHostModule

TRAYPUBLISH_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class TrayPublishModule(OpenPypeModule, IHostModule, ITrayAction):
    label = "New Publish (beta)"
    name = "traypublish_tool"
    host_name = "traypublish"

    def initialize(self, modules_settings):
        self.enabled = True
        self.publish_paths = [
            os.path.join(TRAYPUBLISH_ROOT_DIR, "plugins", "publish")
        ]
        self._experimental_tools = None

    def tray_init(self):
        from openpype.tools.experimental_tools import ExperimentalTools

        self._experimental_tools = ExperimentalTools()

    def tray_menu(self, *args, **kwargs):
        super(TrayPublishModule, self).tray_menu(*args, **kwargs)
        traypublisher = self._experimental_tools.get("traypublisher")
        visible = False
        if traypublisher and traypublisher.enabled:
            visible = True
        self._action_item.setVisible(visible)

    def on_action_trigger(self):
        self.run_traypublisher()

    def connect_with_modules(self, enabled_modules):
        """Collect publish paths from other modules."""
        publish_paths = self.manager.collect_plugin_paths()["publish"]
        self.publish_paths.extend(publish_paths)

    def run_traypublisher(self):
        args = get_openpype_execute_args(
            "module", self.name, "launch"
        )
        run_detached_process(args)

    def cli(self, click_group):
        click_group.add_command(cli_main)


@click.group(TrayPublishModule.name, help="TrayPublisher related commands.")
def cli_main():
    pass


@cli_main.command()
def launch():
    """Launch TrayPublish tool UI."""

    from openpype.tools import traypublisher

    traypublisher.main()
