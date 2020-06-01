from .user_module import UserModule


def tray_init(tray_widget, main_widget):
    return UserModule(main_widget, tray_widget)
