from openpype.modules import OpenPypeModule


class HostsJobServer(OpenPypeModule):
    name = "hosts_job_server"

    def initialize(self, modules_settings):
        self._server_url = modules_settings.get("server_url")
        self.enabled = True

    def start_server(self, port=None, host=None):
        from .job_server import main

        return main(port, host)

    def start_worker(self, app_name, server_url=None):
        from openpype.lib import ApplicationManager

        if server_url is None:
            server_url = self._server_url

        app_manager = ApplicationManager()
        app = app_manager.applications.get(app_name)
        if app is None:
            raise ValueError(
                "Didn't find application \"{}\" in settings.".format(app_name)
            )

        if app.host_name == "tvpaint":
            return self._start_tvpaint_worker(app, server_url)
        raise ValueError("Unknown host \"{}\"".format(app.host_name))

    def _start_tvpaint_worker(self, app, server_url):
        from .job_workers.tvpaint_worker import main

        executable = app.find_executable()
        if not executable:
            raise ValueError((
                "Executable for app \"{}\" is not set"
                " or accessible on this workstation."
            ).format(app.full_name))

        return main(executable, server_url)
