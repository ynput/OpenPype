import json

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
        self.server_manager.add_route(
            "POST",
            self.prefix + "/stop_timer",
            self.stop_timer
        )
        self.server_manager.add_route(
            "GET",
            self.prefix + "/get_task_time",
            self.get_task_time
        )

    async def start_timer(self, request):
        data = await request.json()
        try:
            project_name = data["project_name"]
            asset_name = data["asset_name"]
            task_name = data["task_name"]
        except KeyError:
            msg = (
                "Payload must contain fields 'project_name,"
                " 'asset_name' and 'task_name'"
            )
            log.error(msg)
            return Response(status=400, message=msg)

        self.module.stop_timers()
        try:
            self.module.start_timer(project_name, asset_name, task_name)
        except Exception as exc:
            return Response(status=404, message=str(exc))

        return Response(status=200)

    async def stop_timer(self, request):
        self.module.stop_timers()
        return Response(status=200)

    async def get_task_time(self, request):
        data = await request.json()
        try:
            project_name = data['project_name']
            asset_name = data['asset_name']
            task_name = data['task_name']
        except KeyError:
            message = (
                "Payload must contain fields 'project_name, 'asset_name',"
                " 'task_name'"
            )
            log.warning(message)
            return Response(text=message, status=404)

        time = self.module.get_task_time(project_name, asset_name, task_name)
        return Response(text=json.dumps(time))
