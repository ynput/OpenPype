from aiohttp.web_response import Response
from openpype.api import Logger

log = Logger().get_logger("Event processor")

class TimersManagerModuleRestApi:
    """
        REST API endpoint used for calling from hosts when context change
        happens in Workfile app.
    """
    def __init__(self, user_module, server_manager):
        self.module = user_module
        self.server_manager = server_manager

        self.prefix = "/timers_manager"

        self.register()

    def register(self):
        self.server_manager.add_route(
            "POST",
            self.prefix + "/start_timer",
            self.start_timer
        )

    async def start_timer(self, request):
        data = await request.json()
        try:
            project_name = data['project_name']
            asset_name = data['asset_name']
            task_name = data['task_name']
            hierarchy = data['hierarchy']
        except KeyError:
            log.error("Payload must contain fields 'project_name, " +
                      "'asset_name', 'task_name', 'hierarchy'")
            return Response(status=400)

        self.module.stop_timers()
        self.module.start_timer(project_name, asset_name, task_name, hierarchy)
        return Response(status=200)
