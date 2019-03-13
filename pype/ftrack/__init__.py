from .lib import *
from .ftrack_server import *
from .ftrack_run import FtrackRunner


def tray_init(tray_widget, main_widget):
    ftrack = FtrackRunner(main_widget, tray_widget)
    main_widget.menu.addMenu(ftrack.trayMenu(tray_widget.menu))
    ftrack.validate()
