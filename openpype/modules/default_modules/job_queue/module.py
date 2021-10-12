import sys

if sys.version_info[0] == 2:
    from urlparse import urlsplit, urlunsplit
else:
    from urllib.parse import urlsplit, urlunsplit

import click
from openpype.modules import OpenPypeModule
from openpype.api import get_system_settings


class JobQueueModule(OpenPypeModule):
    name = "job_queue"

    def initialize(self, modules_settings):
        server_url = modules_settings.get("server_url") or ""

        self._server_url = self.url_conversion(server_url)
        self.enabled = True

    @staticmethod
    def url_conversion(url):
        if not url:
            return url

        url_parts = list(urlsplit(url))
        if not url_parts[0]:
            url = "http://{}".format(url)
            url_parts = list(urlsplit(url))

        return urlunsplit(url_parts)

    @property
    def server_url(self):
        return self._server_url

    def send_job(self, host_name, job_data):
        import requests

        job_data = job_data or {}
        job_data["host_name"] = host_name
        api_path = "{}/api/jobs".format(self._server_url)
        job_id = requests.post(api_path, data=job_data)
        return job_id

    def get_job_status(self, job_id):
        import requests

        api_path = "{}/api/jobs/{}".format(self._server_url, job_id)
        return requests.get(api_path)

    def cli(self, click_group):
        click_group.add_command(cli_main)

    @classmethod
    def get_server_url_from_settings(cls):
        module_settings = get_system_settings()["modules"]
        return cls.url_conversion(
            module_settings
            .get(cls.name, {})
            .get("server_url")
        )

    @classmethod
    def start_server(cls, port=None, host=None):
        from .job_server import main

        return main(port, host)

    @classmethod
    def start_worker(cls, app_name, server_url=None):
        import requests
        from openpype.lib import ApplicationManager

        if not server_url:
            server_url = cls.get_server_url_from_settings()

        server_url = "localhost:8079"
        if not server_url:
            raise ValueError("Server url is not set.")

        server_url = cls.url_conversion(server_url)

        # Validate url
        requests.get(server_url)

        app_manager = ApplicationManager()
        app = app_manager.applications.get(app_name)
        if app is None:
            raise ValueError(
                "Didn't find application \"{}\" in settings.".format(app_name)
            )

        if app.host_name == "tvpaint":
            return cls._start_tvpaint_worker(app, server_url)
        raise ValueError("Unknown host \"{}\"".format(app.host_name))

    @classmethod
    def _start_tvpaint_worker(cls, app, server_url):
        from .job_workers.tvpaint_worker import main

        executable = app.find_executable()
        if not executable:
            raise ValueError((
                "Executable for app \"{}\" is not set"
                " or accessible on this workstation."
            ).format(app.full_name))

        return main(str(executable), server_url)


@click.group(
    JobQueueModule.name,
    help="Application job server. Can be used as render farm."
)
def cli_main():
    pass


@cli_main.command(
    "start_server",
    help="Start server handling workers and their jobs."
)
@click.option("--port", help="Server port")
@click.option("--host", help="Server host (ip address)")
def cli_start_server(port, host):
    JobQueueModule.start_server(port, host)


@cli_main.command(
    "start_worker", help=(
        "Start a worker for a specific application. (e.g. \"tvpaint/11.5\")"
    )
)
@click.argument("app_name")
@click.option("--server_url", help="Server url which handle workers and jobs.")
def cli_start_worker(app_name, server_url):
    JobQueueModule.start_worker(app_name, server_url)
