import json
from aiohttp.web_response import Response


class UserModuleRestApi:
    def __init__(self, user_module, server_manager):
        self.module = user_module
        self.server_manager = server_manager

        self.prefix = "/user"

        self.register()

    def register(self):
        self.server_manager.add_route(
            "GET",
            self.prefix + "/username",
            self.get_username
        )
        self.server_manager.add_route(
            "GET",
            self.prefix + "/show_widget",
            self.show_user_widget
        )

    async def get_username(self, request):
        return Response(
            status=200,
            body=json.dumps(self.module.cred, indent=4),
            content_type="application/json"
        )

    async def show_user_widget(self, request):
        self.module.action_show_widget.trigger()
        return Response(status=200)
