from qtpy import QtWidgets, QtGui

from openpype import style
from openpype import resources
from openpype.lib import (
    Logger,
    ApplictionExecutableNotFound,
    ApplicationLaunchFailed
)
from openpype.pipeline import LauncherAction


# TODO move to 'openpype.pipeline.actions'
# - remove Qt related stuff and implement exceptions to show error in launcher
class ApplicationAction(LauncherAction):
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
            self._log = Logger.get_logger(self.__class__.__name__)
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
