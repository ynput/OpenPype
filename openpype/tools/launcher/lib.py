"""Utility script for updating database with configuration files

Until assets are created entirely in the database, this script
provides a bridge between the file-based project inventory and configuration.

- Migrating an old project:
    $ python -m avalon.inventory --extract --silo-parent=f02_prod
    $ python -m avalon.inventory --upload

- Managing an existing project:
    1. Run `python -m avalon.inventory --load`
    2. Update the .inventory.toml or .config.toml
    3. Run `python -m avalon.inventory --save`

"""

import os
from Qt import QtGui, QtCore
from avalon.vendor import qtawesome
from openpype.api import resources

ICON_CACHE = {}
NOT_FOUND = type("NotFound", (object, ), {})


class ProjectHandler(QtCore.QObject):
    """Handler of project model and current project in Launcher tool.

    Helps to organize two separate widgets handling current project selection.

    It is easier to trigger project change callbacks from one place than from
    multiple different places without proper handling or sequence changes.

    Args:
        dbcon(AvalonMongoDB): Mongo connection with Session.
        model(ProjectModel): Object of projects model which is shared across
            all widgets using projects. Arg dbcon should be used as source for
            the model.
    """
    # Project list will be refreshed each 10000 msecs
    # - this is not part of helper implementation but should be used by widgets
    #   that may require reshing of projects
    refresh_interval = 10000

    # Signal emitted when project has changed
    project_changed = QtCore.Signal(str)
    projects_refreshed = QtCore.Signal()
    timer_timeout = QtCore.Signal()

    def __init__(self, dbcon, model):
        super(ProjectHandler, self).__init__()
        self._active = False
        # Store project model for usage
        self.model = model
        # Store dbcon
        self.dbcon = dbcon

        self.current_project = dbcon.Session.get("AVALON_PROJECT")

        refresh_timer = QtCore.QTimer()
        refresh_timer.setInterval(self.refresh_interval)
        refresh_timer.timeout.connect(self._on_timeout)

        self.refresh_timer = refresh_timer

    def _on_timeout(self):
        if self._active:
            self.timer_timeout.emit()
            self.refresh_model()

    def set_active(self, active):
        self._active = active

    def start_timer(self, trigger=False):
        self.refresh_timer.start()
        if trigger:
            self._on_timeout()

    def stop_timer(self):
        self.refresh_timer.stop()

    def set_project(self, project_name):
        # Change current project of this handler
        self.current_project = project_name
        # Change session project to take effect for other widgets using the
        #   dbcon object.
        self.dbcon.Session["AVALON_PROJECT"] = project_name

        # Trigger change signal when everything is updated to new project
        self.project_changed.emit(project_name)

    def refresh_model(self):
        self.model.refresh()
        self.projects_refreshed.emit()


def get_action_icon(action):
    icon_name = action.icon
    if not icon_name:
        return None

    global ICON_CACHE

    icon = ICON_CACHE.get(icon_name)
    if icon is NOT_FOUND:
        return None
    elif icon:
        return icon

    icon_path = resources.get_resource(icon_name)
    if not os.path.exists(icon_path):
        icon_path = icon_name.format(resources.RESOURCES_DIR)

    if os.path.exists(icon_path):
        icon = QtGui.QIcon(icon_path)
        ICON_CACHE[icon_name] = icon
        return icon

    try:
        icon_color = getattr(action, "color", None) or "white"
        icon = qtawesome.icon(
            "fa.{}".format(icon_name), color=icon_color
        )

    except Exception:
        ICON_CACHE[icon_name] = NOT_FOUND
        print("Can't load icon \"{}\"".format(icon_name))

    return icon


def get_action_label(action):
    label = getattr(action, "label", None)
    if not label:
        return action.name

    label_variant = getattr(action, "label_variant", None)
    if not label_variant:
        return label
    return " ".join([label, label_variant])
