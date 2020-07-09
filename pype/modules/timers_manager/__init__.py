from .timers_manager import TimersManager
from .widget_user_idle import WidgetUserIdle

CLASS_DEFINIION = TimersManager


def tray_init(tray_widget, main_widget):
    return TimersManager(tray_widget, main_widget)
