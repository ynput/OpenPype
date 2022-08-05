import os
import subprocess

from openpype.pipeline import LauncherAction


class DebugShell(LauncherAction):
    """Run any host environment in command line."""
    name = "debugshell"
    label = "Shell"
    icon = "terminal"
    color = "#e8770e"
    order = 10

    def is_compatible(self, session):
        required = {"AVALON_PROJECT", "AVALON_ASSET", "AVALON_TASK"}
        return required.issubset(session)

    def process(self, session, **kwargs):
        from openpype.api import get_app_environments_for_context

        # Get the environment
        project = session["AVALON_PROJECT"]
        asset = session["AVALON_ASSET"]
        task = session["AVALON_TASK"]

        applications = self.get_applications(project)
        result = self.choose_app(applications)
        if not result:
            return

        app_name, app = result
        print(f"Retrieving environment for: {app_name}..")
        env = get_app_environments_for_context(project, asset, task, app_name)

        # If an executable is found. Then add the parent folder to PATH
        # just so we can run the application easily from the command line.
        exe = app.find_executable()
        if exe:
            exe_path = exe._realpath()
            folder = os.path.dirname(exe_path)
            print(f"Appending to PATH: {folder}")
            env["PATH"] += os.pathsep + folder

        cwd = env.get("AVALON_WORKDIR")
        if cwd:
            print(f"Setting Work Directory: {cwd}")

        print(f"Launch cmd in environment of {app_name}..")
        subprocess.Popen("cmd",
                         env=env,
                         cwd=cwd,
                         creationflags=subprocess.CREATE_NEW_CONSOLE)

    def choose_app(self, applications):
        import openpype.style
        from Qt import QtWidgets, QtGui
        from openpype.tools.launcher.lib import get_action_icon

        menu = QtWidgets.QMenu()
        menu.setStyleSheet(openpype.style.load_stylesheet())

        # Sort applications
        applications = sorted(
            applications.items(),
            key=lambda item: item[1].name
        )

        for app_name, app in applications:
            label = f"{app.group.label} {app.label}"
            icon = get_action_icon(app)

            menu_action = QtWidgets.QAction(label, parent=menu)
            if icon:
                menu_action.setIcon(icon)
            menu_action.setData((app_name, app))
            menu.addAction(menu_action)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            return result.data()

    def get_applications(self, project_name):
        from openpype.pipeline import AvalonMongoDB
        from openpype.lib import ApplicationManager

        # Get applications
        manager = ApplicationManager()
        manager.refresh()

        # Create mongo connection
        dbcon = AvalonMongoDB()
        dbcon.Session["AVALON_PROJECT"] = project_name
        project_doc = dbcon.find_one({"type": "project"})
        assert project_doc, "Project not found. This is a bug."

        # Filter to apps valid for this current project, with logic from:
        # `openpype.tools.launcher.models.ActionModel.get_application_actions`
        project_doc = dbcon.find_one(
            {"type": "project"},
            {"config.apps": True}
        )
        if not project_doc:
            return {}

        applications = {}
        for app_def in project_doc["config"]["apps"]:
            app_name = app_def["name"]
            app = manager.applications.get(app_name)
            if not app or not app.enabled:
                continue
            applications[app_name] = app

        return applications
