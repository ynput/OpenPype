from .asapublish_module import ASAPublishModule
from .app import (
    show,
    cli
)
__all__ = [
    "show",
    "cli"
]

def tray_init(tray_widget, main_widget):
    return ASAPublishModule(main_widget, tray_widget)
