import os
import platform
import subprocess

from openpype.client import (
    get_project,
    get_asset_by_name,
)
from openpype.pipeline import (
    Anatomy,
    LauncherAction,
)
from openpype.pipeline.template_data import get_template_data


class OpenTaskPath(LauncherAction):
    name = "open_task_path"
    label = "Explore here"
    icon = "folder-open"
    order = 500

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        return "AVALON_ASSET" in session

    def process(self, session, **kwargs):
        from qtpy import QtCore, QtWidgets

        project_name = session["AVALON_PROJECT"]
        asset_name = session.get("AVALON_ASSET", None)
        task_name = session.get("AVALON_TASK", None)

        project = get_project(project_name)
        asset = get_asset_by_name(project_name, asset_name)

        data = get_template_data(project, asset, task_name)

        anatomy = Anatomy(project_name)
        workdir = anatomy.templates_obj["work"]["folder"].format(data)

        # Remove any potential unformatted parts of the path
        valid_workdir = workdir.split("{", 1)[0]

        # Path is not filled
        if not valid_workdir:
            return

        # Normalize
        valid_workdir = os.path.normpath(valid_workdir)
        while not os.path.exists(valid_workdir):
            prev_workdir = valid_workdir
            valid_workdir = os.path.dirname(prev_workdir)
            if not valid_workdir or valid_workdir == prev_workdir:
                return None

        path = valid_workdir

        app = QtWidgets.QApplication.instance()
        ctrl_pressed = QtCore.Qt.ControlModifier & app.keyboardModifiers()
        if ctrl_pressed:
            # Copy path to clipboard
            self.copy_path_to_clipboard(path)
        else:
            self.open_in_explorer(path)

    @staticmethod
    def open_in_explorer(path):
        platform_name = platform.system().lower()
        if platform_name == "windows":
            args = ["start", path]
        elif platform_name == "darwin":
            args = ["open", "-na", path]
        elif platform_name == "linux":
            args = ["xdg-open", path]
        else:
            raise RuntimeError(f"Unknown platform {platform.system()}")
        # Make sure path is converted correctly for 'os.system'
        os.system(subprocess.list2cmdline(args))

    @staticmethod
    def copy_path_to_clipboard(path):
        from qtpy import QtWidgets

        path = path.replace("\\", "/")
        print(f"Copied to clipboard: {path}")
        app = QtWidgets.QApplication.instance()
        assert app, "Must have running QApplication instance"

        # Set to Clipboard
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(os.path.normpath(path))
