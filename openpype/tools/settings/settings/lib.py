from Qt import QtCore

from .widgets import SettingsToolBtn

# Offset of value change trigger in ms
VALUE_CHANGE_OFFSET_MS = 300


def create_deffered_value_change_timer(callback):
    """Defer value change callback.

    UI won't trigger all callbacks on each value change but after predefined
    time. Timer is reset on each start so callback is triggered after user
    finish editing.
    """
    timer = QtCore.QTimer()
    timer.setSingleShot(True)
    timer.setInterval(VALUE_CHANGE_OFFSET_MS)
    timer.timeout.connect(callback)
    return timer


def create_add_btn(parent):
    add_btn = SettingsToolBtn("add", parent)
    add_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
    return add_btn


def create_remove_btn(parent):
    remove_btn = SettingsToolBtn("remove", parent)
    remove_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
    return remove_btn


def create_up_btn(parent):
    remove_btn = SettingsToolBtn("up", parent)
    remove_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
    return remove_btn


def create_down_btn(parent):
    add_btn = SettingsToolBtn("down", parent)
    add_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
    return add_btn


def create_confirm_btn(parent):
    remove_btn = SettingsToolBtn("confirm", parent)
    remove_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
    return remove_btn
