from .timers_manager import TimersManager

CLASS_DEFINIION = TimersManager


def tray_init(tray_widget, main_widget):
    return TimersManager(tray_widget, main_widget)
