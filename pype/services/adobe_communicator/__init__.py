from .lib import PUBLISH_PATHS

from .adobe_comunicator import AdobeCommunicator

__all__ = [
    "PUBLISH_PATHS"
]


def tray_init(tray_widget, main_widget):
    return AdobeCommunicator()
