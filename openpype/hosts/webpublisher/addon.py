import os

import click

from openpype.modules import OpenPypeModule
from openpype.modules.interfaces import IHostModule

WEBPUBLISHER_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class WebpublisherAddon(OpenPypeModule, IHostModule):
    name = "webpublisher"
    host_name = "webpublisher"

    def initialize(self, module_settings):
        self.enabled = True

    def cli(self, click_group):
        click_group.add_command(cli_main)


@click.group(
    WebpublisherAddon.name,
    help="Webpublisher related commands.")
def cli_main():
    pass


@cli_main.command()
@click.argument("path")
@click.option("-u", "--user", help="User email address")
@click.option("-p", "--project", help="Project")
@click.option("-t", "--targets", help="Targets", default=None,
              multiple=True)
def publish(project, path, user=None, targets=None):
    """Start CLI publishing.

    Publish collects json from paths provided as an argument.
    More than one path is allowed.
    """

    from .cli_functions import cli_publish

    cli_publish(project, path, user, targets)


@cli_main.command()
@click.argument("path")
@click.option("-h", "--host", help="Host")
@click.option("-u", "--user", help="User email address")
@click.option("-p", "--project", help="Project")
@click.option("-t", "--targets", help="Targets", default=None,
              multiple=True)
def publishfromapp(project, path, user=None, targets=None):
    """Start CLI publishing.

    Publish collects json from paths provided as an argument.
    More than one path is allowed.
    """

    from .cli_functions import cli_publish_from_app

    cli_publish_from_app(project, path, user, targets)
