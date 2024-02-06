import os

from openpype import AYON_SERVER_ENABLED
from openpype.lib import get_openpype_execute_args
from openpype.lib.execute import run_detached_process
from openpype.modules import (
    click_wrap,
    OpenPypeModule,
    ITrayAction,
    IHostAddon,
)

TRAYPUBLISH_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class TrayPublishAddon(OpenPypeModule, IHostAddon, ITrayAction):
    label = "Publisher"
    name = "traypublisher"
    host_name = "traypublisher"

    def initialize(self, modules_settings):
        self.enabled = True
        self.publish_paths = [
            os.path.join(TRAYPUBLISH_ROOT_DIR, "plugins", "publish")
        ]

    def tray_init(self):
        return

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
        click_group.add_command(cli_main.to_click_obj())


@click_wrap.group(
    TrayPublishAddon.name,
    help="TrayPublisher related commands.")
def cli_main():
    pass


@cli_main.command()
def launch():
    """Launch TrayPublish tool UI."""

    from openpype.tools import traypublisher

    traypublisher.main()


@cli_main.command()
@click_wrap.option(
    "--csv-filepath",
    help="Full path to CSV file with data",
    type=click.Path(exists=True),
    required=True
)
@click_wrap.option(
    "--project-name",
    help="Project name in which the context will be used",
    type=str,
    required=True
)
@click_wrap.option(
    "--asset-name",
    help="Asset name in which the context will be used",
    type=str,
    required=True
)
@click_wrap.option(
    "--task-name",
    help="Task name under Asset in which the context will be used",
    type=str,
    required=False
)
@click_wrap.option(
    "--ignore-validators",
    help="Option to ignore validators",
    type=bool,
    is_flag=True,
    required=False
)
def ingestcsv(
    csv_filepath,
    project_name,
    asset_name,
    task_name,
    ignore_validators
):
    """Ingest CSV file into project.

    This command will ingest CSV file into project. CSV file must be in
    specific format. See documentation for more information.
    """
    if AYON_SERVER_ENABLED:
        raise RuntimeError(
            "This feature is not supported in Ayon yet. "
            "Contact support for more info."
        )

    from .csv_publish import csvpublish

    csvpublish(
        csv_filepath,
        project_name,
        asset_name,
        task_name,
        ignore_validators
    )
