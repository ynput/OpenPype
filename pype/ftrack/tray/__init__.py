from .ftrack_module import FtrackModule


def tray_init(tray_widget, main_widget):
    return FtrackModule(main_widget, tray_widget)
