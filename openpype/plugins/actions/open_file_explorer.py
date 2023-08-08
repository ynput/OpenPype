import os
import platform
import subprocess
import getpass

from openpype.client import (
    get_project,
    get_asset_by_name,
)
from openpype.pipeline import (
    Anatomy,
    LauncherAction,
)


class OpenTaskPath(LauncherAction):
    name = "open_task_path"
    label = "Open in File Browser"
    icon = None
    order = 500

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        return "AVALON_ASSET" in session

    def process(self, session, **kwargs):
        from qtpy import QtCore, QtWidgets

        project_name = session["AVALON_PROJECT"]
        asset_name = session.get("AVALON_ASSET", None)
        task_name = session.get("AVALON_TASK", None)
        host_name = None    # never present in session

        project = get_project(project_name)
        asset = get_asset_by_name(project_name, asset_name)

        data = self.get_workdir_data(project_doc=project,
                                     asset_doc=asset,
                                     task_name=task_name,
                                     host_name=host_name)
        anatomy = Anatomy(project_name)
        result = anatomy.format(data)

        # todo: implement custom template keys instead of 'work'
        # Get template key
        # template_key = get_workfile_template_key_from_context(
        #    asset_name, task_name, host_name, project_name, dbcon
        # )
        workdir = result["work"]["folder"]

        # Keep only the part of the path that was formatted by splitting up to
        # the first stub - we can only explore up to there
        STUB = "<<NULL>>"
        valid_dir = workdir.split(STUB, 1)[0]

        # If the unformatted data left us with half a folder name or file name
        # after splitting then we get the dirname.
        if not valid_dir.replace("\\", "/").endswith("/"):
            valid_dir = os.path.dirname(valid_dir)

        # If the path endswith `/work` and the path does not exist but the
        # parent does then we allow to go to the parent because it could for
        # example be the hierarchical folder for `asset` in e.g. `asset/hero`
        if not os.path.exists(valid_dir) and valid_dir.endswith("/work/"):
            # /folder/ dirname is /folder so we rstrip the last / to be sure
            parent_dir = os.path.dirname(valid_dir.rstrip("/"))
            if os.path.exists(parent_dir):
                valid_dir = parent_dir

        path = os.path.normpath(valid_dir)

        app = QtWidgets.QApplication.instance()
        ctrl_pressed = QtCore.Qt.ControlModifier & app.keyboardModifiers()
        if ctrl_pressed:
            # Copy path to clipboard
            self.copy_path_to_clipboard(path)
        else:
            self.open_in_explorer(path)

    def get_workdir_data(self, project_doc, asset_doc, task_name, host_name):
        """Mimic `openpype.lib.get_workdir_data` but require less data.

        This allows for example to have only a valid `project_doc` passed in
        and the rest being None. For all that is None a stub placeholder data
        value will be returned.

        Returns:
            dict: Workdir data.

        """

        # Start with mostly stub placeholder data where we cannot match
        # `openpype.lib.get_workdir_data` due to lack of input variables.
        STUB = "<<NULL>>"
        data = {
            "project": {
                "name": project_doc["name"],
                "code": project_doc["data"].get("code")
            },
            "task": {
                "name": STUB,
                "type": STUB,
                "short": STUB,
            },
            "asset": STUB,
            "parent": STUB,
            "hierarchy": STUB,
            "app": STUB,
            "user": getpass.getuser()
        }

        # Retrieve data similar to `openpype.lib.get_workdir_data` but only
        # up to where we can. First using AVALON_ASSET in session.
        if asset_doc:
            asset_parents = asset_doc["data"]["parents"]
            hierarchy = "/".join(asset_parents)

            parent_name = project_doc["name"]
            if asset_parents:
                parent_name = asset_parents[-1]

            # Insert asset data
            data.update({
                "asset": asset_doc["name"],
                "parent": parent_name,
                "hierarchy": hierarchy,
            })

        # Then insert task data when AVALON_TASK in session
        if asset_doc and task_name is not None:
            asset_tasks = asset_doc['data']['tasks']
            task_type = asset_tasks.get(task_name, {}).get('type')
            project_task_types = project_doc["config"]["tasks"]
            task_code = project_task_types.get(task_type, {}).get(
                "short_name"
            )

            # Insert task data
            data["task"].update({
                "name": task_name,
                "type": task_type,
                "code": task_code
            })

        return data

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
