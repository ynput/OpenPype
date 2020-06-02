PUBLISH_PATHS = []

from .standalonepublish_module import StandAlonePublishModule
from .app import (
    show,
    cli
)
__all__ = [
    "show",
    "cli"
]

def tray_init(tray_widget, main_widget):
    return StandAlonePublishModule(main_widget, tray_widget)
