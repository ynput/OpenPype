import os

from avalon import api
from openpype import PLUGINS_DIR
from openpype import style
from openpype.api import Logger, resources
from openpype.lib import (
    ApplictionExecutableNotFound,
    ApplicationLaunchFailed
)
from Qt import QtWidgets, QtGui


def register_actions_from_paths(paths):
    if not paths:
        return

    for path in paths:
        if not path:
            continue

        if path.startswith("."):
            print((
                "BUG: Relative paths are not allowed for security reasons. {}"
            ).format(path))
            continue

        if not os.path.exists(path):
            print("Path was not found: {}".format(path))
            continue

        api.register_plugin_path(api.Action, path)


def register_config_actions():
    """Register actions from the configuration for Launcher"""

    actions_dir = os.path.join(PLUGINS_DIR, "actions")
    register_actions_from_paths([actions_dir])


def register_environment_actions():
    """Register actions from AVALON_ACTIONS for Launcher."""

    paths_str = os.environ.get("AVALON_ACTIONS") or ""
    register_actions_from_paths(paths_str.split(os.pathsep))


class ApplicationAction(api.Action):
    """Pype's application launcher

    Application action based on pype's ApplicationManager system.
    """

    # Application object
    application = None
    # Action attributes
    name = None
    label = None
    label_variant = None
    group = None
    icon = None
    color = None
    order = 0
    data = {}

    _log = None
    required_session_keys = (
        "AVALON_PROJECT",
        "AVALON_ASSET",
        "AVALON_TASK"
    )

    @property
    def log(self):
        if self._log is None:
            self._log = Logger().get_logger(self.__class__.__name__)
        return self._log

    def is_compatible(self, session):
        for key in self.required_session_keys:
            if key not in session:
                return False
        return True

    def _show_message_box(self, title, message, details=None):
        dialog = QtWidgets.QMessageBox()
        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        dialog.setWindowIcon(icon)
        dialog.setStyleSheet(style.load_stylesheet())
        dialog.setWindowTitle(title)
        dialog.setText(message)
        if details:
            dialog.setDetailedText(details)
        dialog.exec_()

    def process(self, session, **kwargs):
        """Process the full Application action"""

        project_name = session["AVALON_PROJECT"]
        asset_name = session["AVALON_ASSET"]
        task_name = session["AVALON_TASK"]
        try:
            self.application.launch(
                project_name=project_name,
                asset_name=asset_name,
                task_name=task_name,
                **self.data
            )

        except ApplictionExecutableNotFound as exc:
            details = exc.details
            msg = exc.msg
            log_msg = str(msg)
            if details:
                log_msg += "\n" + details
            self.log.warning(log_msg)
            self._show_message_box(
                "Application executable not found", msg, details
            )

        except ApplicationLaunchFailed as exc:
            msg = str(exc)
            self.log.warning(msg, exc_info=True)
            self._show_message_box("Application launch failed", msg)
