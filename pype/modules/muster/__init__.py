from .muster import MusterModule


def tray_init(tray_widget, main_widget):
    return MusterModule(main_widget, tray_widget)
