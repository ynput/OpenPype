import os
import appdirs


CLOCKIFY_FTRACK_SERVER_PATH = os.path.join(
    os.path.dirname(__file__), "ftrack", "server"
)
CLOCKIFY_FTRACK_USER_PATH = os.path.join(
    os.path.dirname(__file__), "ftrack", "user"
)
CREDENTIALS_JSON_PATH = os.path.normpath(os.path.join(
    appdirs.user_data_dir("pype-app", "pype"),
    "clockify.json"
))

ADMIN_PERMISSION_NAMES = ["WORKSPACE_OWN", "WORKSPACE_ADMIN"]
CLOCKIFY_ENDPOINT = "https://api.clockify.me/api/"
