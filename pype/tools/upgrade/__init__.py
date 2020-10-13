from . import executor


def tray_init(tray_widget, main_widget):  # TODO shouldn't be on tray init
    return executor.UpgradeExecutor()
