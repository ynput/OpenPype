import os


CLOCKIFY_FTRACK_SERVER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "ftrack", "server"
)
CLOCKIFY_FTRACK_USER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "ftrack", "user"
)

ADMIN_PERMISSION_NAMES = ["WORKSPACE_OWN", "WORKSPACE_ADMIN"]
CLOCKIFY_ENDPOINT = "https://api.clockify.me/api/"
