from .clockify import ClockifyModule

CLASS_DEFINIION = ClockifyModule


def tray_init(tray_widget, main_widget):
    return ClockifyModule(main_widget, tray_widget)
