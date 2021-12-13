"""Job queue OpenPype module was created for remote execution of commands.

## Why is needed
Primarily created for hosts which are not easilly controlled from command line
or in headless mode and is easier to keep one process of host running listening
for jobs to do.

### Example
One of examples is TVPaint which does not have headless mode, can run only one
process at one time and it's impossible to know what should be executed inside
TVPaint before we know all data about the file that should be processed.

## Idea
Idea is that there is a server, workers and workstation/s which need to process
something on a worker.

Workers and workstation/s must have access to server through adress to it's
running instance. Workers use WebSockets and workstations are using HTTP calls.
Also both of them must have access to job queue root which is set in
settings. Root is used as temp where files needed for job can be stored before
sending the job or where result files are stored when job is done.

Server's address must be set in settings when is running so workers and
workstations know where to send or receive jobs.

## Command line commands
### start_server
- start server which is handles jobs
- it is possible to specify port and host address (default is localhost:8079)

### start_worker
- start worker which will process jobs
- has required possitional argument which is application name from OpenPype
    settings e.g. 'tvpaint/11-5' ('tvpaint' is group '11-5' is variant)
- it is possible to specify server url but url from settings is used when not
    passed (this is added mainly for developing purposes)
"""

import sys
import json
import copy
import platform

import click
from openpype.modules import OpenPypeModule
from openpype.api import get_system_settings


class JobQueueModule(OpenPypeModule):
    name = "job_queue"

    def initialize(self, modules_settings):
        module_settings = modules_settings.get(self.name) or {}
        server_url = module_settings.get("server_url") or ""

        self._server_url = self.url_conversion(server_url)
        jobs_root_mapping = self._roots_mapping_conversion(
            module_settings.get("jobs_root")
        )

        self._jobs_root_mapping = jobs_root_mapping

        # Is always enabled
        #   - the module does nothing until is used
        self.enabled = True

    @classmethod
    def _root_conversion(cls, root_path):
        """Make sure root path does not end with slash."""
        # Return empty string if path is invalid
        if not root_path:
            return ""

        # Remove all slashes
        while root_path.endswith("/") or root_path.endswith("\\"):
            root_path = root_path[:-1]
        return root_path

    @classmethod
    def _roots_mapping_conversion(cls, roots_mapping):
        roots_mapping = roots_mapping or {}
        for platform_name in ("windows", "linux", "darwin"):
            roots_mapping[platform_name] = cls._root_conversion(
                roots_mapping.get(platform_name)
            )
        return roots_mapping

    @staticmethod
    def url_conversion(url, ws=False):
        if sys.version_info[0] == 2:
            from urlparse import urlsplit, urlunsplit
        else:
            from urllib.parse import urlsplit, urlunsplit

        if not url:
            return url

        url_parts = list(urlsplit(url))
        scheme = url_parts[0]
        if not scheme:
            if ws:
                url = "ws://{}".format(url)
            else:
                url = "http://{}".format(url)
            url_parts = list(urlsplit(url))

        elif ws:
            if scheme not in ("ws", "wss"):
                if scheme == "https":
                    url_parts[0] = "wss"
                else:
                    url_parts[0] = "ws"

        elif scheme not in ("http", "https"):
            if scheme == "wss":
                url_parts[0] = "https"
            else:
                url_parts[0] = "http"

        return urlunsplit(url_parts)

    def get_jobs_root_mapping(self):
        return copy.deepcopy(self._jobs_root_mapping)

    def get_jobs_root(self):
        return self._jobs_root_mapping.get(platform.system().lower())

    @classmethod
    def get_jobs_root_from_settings(cls):
        module_settings = get_system_settings()["modules"]
        jobs_root_mapping = module_settings.get(cls.name, {}).get("jobs_root")
        converted_mapping = cls._roots_mapping_conversion(jobs_root_mapping)

        return converted_mapping[platform.system().lower()]

    @property
    def server_url(self):
        return self._server_url

    def send_job(self, host_name, job_data):
        import requests

        job_data = job_data or {}
        job_data["host_name"] = host_name
        api_path = "{}/api/jobs".format(self._server_url)
        post_request = requests.post(api_path, data=json.dumps(job_data))
        return str(post_request.content.decode())

    def get_job_status(self, job_id):
        import requests

        api_path = "{}/api/jobs/{}".format(self._server_url, job_id)
        return requests.get(api_path).json()

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

        if not server_url:
            raise ValueError("Server url is not set.")

        http_server_url = cls.url_conversion(server_url)

        # Validate url
        requests.get(http_server_url)

        ws_server_url = cls.url_conversion(server_url) + "/ws"

        app_manager = ApplicationManager()
        app = app_manager.applications.get(app_name)
        if app is None:
            raise ValueError(
                "Didn't find application \"{}\" in settings.".format(app_name)
            )

        if app.host_name == "tvpaint":
            return cls._start_tvpaint_worker(app, ws_server_url)
        raise ValueError("Unknown host \"{}\"".format(app.host_name))

    @classmethod
    def _start_tvpaint_worker(cls, app, server_url):
        from openpype.hosts.tvpaint.worker import main

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
