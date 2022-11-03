from aiohttp.web_response import Response
from openpype.lib import Logger


class SyncServerModuleRestApi:
    """
    REST API endpoint used for calling from hosts when context change
    happens in Workfile app.
    """

    def __init__(self, user_module, server_manager):
        self._log = None
        self.module = user_module
        self.server_manager = server_manager

        self.prefix = "/sync_server"

        self.register()

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    def register(self):
        self.server_manager.add_route(
            "POST",
            self.prefix + "/add_sites_to_representations",
            self.add_sites_to_representations,
        )
        self.server_manager.add_route(
            "GET",
            self.prefix + "/files_are_processed",
            self.files_are_processed,
        )

    async def add_sites_to_representations(self, request):
        # Extract data from request
        data = await request.json()
        try:
            project_name = data["project_name"]
            sites = data["sites"]
            representations = data["representations"]
        except KeyError:
            msg = (
                "Payload must contain fields 'project_name,"
                " 'sites' (list of names) and 'representations' (list of IDs)"
            )
            self.log.error(msg)
            return Response(status=400, message=msg)

        # Add all sites to each representation
        for representation_id in representations:
            for site in sites:
                self.module.add_site(
                    project_name, representation_id, site, force=True
                )

        # Force timer to run immediately
        self.module.reset_timer()

        return Response(status=200)

    async def files_are_processed(self, _request):
        return Response(
            body=bytes(self.module.sync_server_thread.files_are_processed)
        )
