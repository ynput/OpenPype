from .avalon_app import AvalonApps


def tray_init(tray_widget, main_widget, parent_menu):
    av_apps = AvalonApps(main_widget, tray_widget)
    av_apps.tray_menu(tray_widget.menu)

    return av_apps
