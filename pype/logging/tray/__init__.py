from .logging_module import LoggingModule


def tray_init(tray_widget, main_widget):
    return LoggingModule(main_widget, tray_widget)
