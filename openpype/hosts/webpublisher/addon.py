import os

from openpype.modules import click_wrap, OpenPypeModule, IHostAddon

WEBPUBLISHER_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class WebpublisherAddon(OpenPypeModule, IHostAddon):
    name = "webpublisher"
    host_name = "webpublisher"

    def initialize(self, module_settings):
        self.enabled = True

    def headless_publish(self, log, close_plugin_name=None, is_test=False):
        """Runs publish in a opened host with a context.

        Close Python process at the end.
        """

        from .lib import get_webpublish_conn, publish_and_log, publish_in_test

        if is_test:
            publish_in_test(log, close_plugin_name)
            return

        dbcon = get_webpublish_conn()
        _id = os.environ.get("BATCH_LOG_ID")
        if not _id:
            log.warning("Unable to store log records, "
                        "batch will be unfinished!")
            return

        publish_and_log(
            dbcon, _id, log, close_plugin_name=close_plugin_name
        )

    def cli(self, click_group):
        click_group.add_command(cli_main.to_click_obj())


@click_wrap.group(
    WebpublisherAddon.name,
    help="Webpublisher related commands.")
def cli_main():
    pass


@cli_main.command()
@click_wrap.argument("path")
@click_wrap.option("-u", "--user", help="User email address")
@click_wrap.option("-p", "--project", help="Project")
@click_wrap.option("-t", "--targets", help="Targets", default=None,
              multiple=True)
def publish(project, path, user=None, targets=None):
    """Start publishing (Inner command).

    Publish collects json from paths provided as an argument.
    More than one path is allowed.
    """

    from .publish_functions import cli_publish

    cli_publish(project, path, user, targets)


@cli_main.command()
@click_wrap.argument("path")
@click_wrap.option("-p", "--project", help="Project")
@click_wrap.option("-h", "--host", help="Host")
@click_wrap.option("-u", "--user", help="User email address")
@click_wrap.option("-t", "--targets", help="Targets", default=None,
              multiple=True)
def publishfromapp(project, path, host, user=None, targets=None):
    """Start publishing through application (Inner command).

    Publish collects json from paths provided as an argument.
    More than one path is allowed.
    """

    from .publish_functions import cli_publish_from_app

    cli_publish_from_app(project, path, host, user, targets)


@cli_main.command()
@click_wrap.option("-e", "--executable", help="Executable")
@click_wrap.option("-u", "--upload_dir", help="Upload dir")
@click_wrap.option("-h", "--host", help="Host", default=None)
@click_wrap.option("-p", "--port", help="Port", default=None)
def webserver(executable, upload_dir, host=None, port=None):
    """Start service for communication with Webpublish Front end.

        OP must be congigured on a machine, eg. OPENPYPE_MONGO filled AND
        FTRACK_BOT_API_KEY provided with api key from Ftrack.

        Expect "pype.club" user created on Ftrack.
    """

    from .webserver_service import run_webserver

    run_webserver(executable, upload_dir, host, port)
