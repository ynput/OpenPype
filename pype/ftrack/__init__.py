from .lib import *
from .ftrack_server import *
from .ftrack_run import FtrackRunner


def tray_init(tray_widget, main_widget, parent_menu):
    ftrack = FtrackRunner(main_widget, tray_widget)
    main_widget.menu.addMenu(ftrack.trayMenu(parent_menu))
    ftrack.validate()

    return ftrack
