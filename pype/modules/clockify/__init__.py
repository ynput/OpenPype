from .constants import (
    CLOCKIFY_ENDPOINT,
    ADMIN_PERMISSION_NAMES,
    CREDENTIALS_JSON_PATH,
    CLOCKIFY_FTRACK_USER_PATH,
    CLOCKIFY_FTRACK_SERVER_PATH
)
from .clockify_api import ClockifyAPI
from .widget_settings import ClockifySettings
from .widget_message import MessageWidget
from .clockify import ClockifyModule

CLASS_DEFINIION = ClockifyModule


def tray_init(tray_widget, main_widget):
    return ClockifyModule(main_widget, tray_widget)
