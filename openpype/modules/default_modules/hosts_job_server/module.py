import click
from openpype.modules import OpenPypeModule
from openpype.api import get_system_settings


class HostsJobServer(OpenPypeModule):
    name = "hosts_job_server"

    def initialize(self, modules_settings):
        server_url = modules_settings.get("server_url") or ""
        while server_url.endswith("/"):
            server_url = server_url[:-1]
        self._server_url = server_url
        self.enabled = True

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
        return (
            module_settings
            .get("hosts_job_server", {})
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

        if server_url is None:
            server_url = cls.get_server_url_from_settings()

        if not server_url:
            raise ValueError("Server url is not set.")

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

        return main(executable, server_url)


@click.group(
    "hosts_job_server",
    help="Application job server. Can be used as render farm."
)
def cli_main():
    pass


@cli_main.command(
    "start_server",
    help="Start server handling workers and their jobs."
)
@click.option("--host", help="Server host (ip address)")
@click.option("--port", help="Server port")
def cli_start_server(host, port):
    HostsJobServer.start_server(host, port)


@cli_main.command(
    "start_worker", help=(
        "Start a worker for a specific application. (e.g. \"tvpaint/11.5\")"
    )
)
@click.argument("app_name")
@click.option("--server_url", help="Server url which handle workers and jobs.")
def cli_start_worker(app_name, server_url):
    HostsJobServer.start_worker(app_name, server_url)
