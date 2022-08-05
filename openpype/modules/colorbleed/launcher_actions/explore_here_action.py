import os
import getpass

from openpype.pipeline import LauncherAction

STUB = "<<NULL>>"


class ExploreToCurrent(LauncherAction):
    name = "exploretocurrent"
    label = "Explore Here"
    icon = "external-link"
    color = "#e8770e"
    order = 7

    def is_compatible(self, session):
        return "AVALON_PROJECT" in session

    def process(self, session, **kwargs):

        from Qt import QtCore, QtWidgets
        from openpype.pipeline import AvalonMongoDB
        from openpype.api import Anatomy

        # Prerequirements
        project_name = session["AVALON_PROJECT"]
        asset_name = session.get("AVALON_ASSET", None)
        task_name = session.get("AVALON_TASK", None)
        host_name = None    # never present in session

        # Create mongo connection
        dbcon = AvalonMongoDB()
        dbcon.Session["AVALON_PROJECT"] = project_name
        project_doc = dbcon.find_one({"type": "project"})
        assert project_doc, "Project not found. This is a bug."

        asset_doc = None
        if asset_name is not None:
            asset_doc = dbcon.find_one({"name": asset_name, "type": "asset"})

        data = self.get_workdir_data(project_doc=project_doc,
                                     asset_doc=asset_doc,
                                     task_name=task_name,
                                     host_name=host_name)
        anatomy = Anatomy(project_name)
        result = anatomy.format(data)

        # todo: implement custom template keys instead of 'work'
        # Get template key
        #template_key = get_workfile_template_key_from_context(
        #    asset_name, task_name, host_name, project_name, dbcon
        #)
        workdir = result["work"]["folder"]

        # Keep only the part of the path that was formatted y splitting up to
        # the first stub - we can only explore up to there
        valid_dir = workdir.split(STUB, 1)[0]

        # If the unformatted data left us with half a folder name or file name
        # after splitting then we get the dirname.
        if not valid_dir.replace("\\", "/").endswith("/"):
            valid_dir = os.path.dirname(valid_dir)

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
        import subprocess

        if os.path.exists(path):
            print("Opening Explorer: %s" % path)
            # todo(roy): Make this cross OS compatible (currently windows only)
            subprocess.Popen(r'explorer "{}"'.format(path))

        else:
            print("Path does not exist: %s" % path)
            raise RuntimeError("Folder does not exist.")

    @staticmethod
    def copy_path_to_clipboard(path):
        from Qt import QtCore, QtWidgets

        path = path.replace("\\", "/")
        print("Copied to clipboard: %s" % path)
        app = QtWidgets.QApplication.instance()
        assert app, "Must have running QApplication instance"

        # Set to Clipboard
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(os.path.normpath(path))
