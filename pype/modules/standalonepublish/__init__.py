from .standalonepublish_module import StandAlonePublishModule


def tray_init(tray_widget, main_widget):
    return StandAlonePublishModule(main_widget, tray_widget)
