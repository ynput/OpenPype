from .idle_manager import IdleManager


def tray_init(tray_widget, main_widget):
    manager = IdleManager()
    manager.start()
    return manager
