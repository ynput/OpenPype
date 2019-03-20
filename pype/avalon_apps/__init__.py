from .avalon_app import AvalonApps


def tray_init(tray_widget, main_widget):
    return AvalonApps(main_widget, tray_widget)
