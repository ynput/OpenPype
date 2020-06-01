from .clockify_api import ClockifyAPI
from .widget_settings import ClockifySettings
from .widget_message import MessageWidget
from .clockify import ClockifyModule

__all__ = [
    "ClockifyAPI",
    "ClockifySettings",
    "ClockifyModule",
    "MessageWidget"
]
    
def tray_init(tray_widget, main_widget):
    return ClockifyModule(main_widget, tray_widget)
