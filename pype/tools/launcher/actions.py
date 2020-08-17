import os
import importlib

from avalon import api, lib


class ProjectManagerAction(api.Action):
    name = "projectmanager"
    label = "Project Manager"
    icon = "gear"
    order = 999     # at the end

    def is_compatible(self, session):
        return "AVALON_PROJECT" in session

    def process(self, session, **kwargs):
        return lib.launch(
            executable="python",
            args=[
                "-u", "-m", "avalon.tools.projectmanager",
                session['AVALON_PROJECT']
            ]
        )


class LoaderAction(api.Action):
    name = "loader"
    label = "Loader"
    icon = "cloud-download"
    order = 998

    def is_compatible(self, session):
        return "AVALON_PROJECT" in session

    def process(self, session, **kwargs):
        return lib.launch(
            executable="python",
            args=[
                "-u", "-m", "avalon.tools.loader", session['AVALON_PROJECT']
            ]
        )


class LoaderLibrary(api.Action):
    name = "loader_os"
    label = "Library Loader"
    icon = "book"
    order = 997     # at the end

    def is_compatible(self, session):
        return True

    def process(self, session, **kwargs):
        return lib.launch(
            executable="python",
            args=["-u", "-m", "avalon.tools.libraryloader"]
        )


def register_default_actions():
    """Register default actions for Launcher"""
    api.register_plugin(api.Action, ProjectManagerAction)
    api.register_plugin(api.Action, LoaderAction)
    api.register_plugin(api.Action, LoaderLibrary)


def register_config_actions():
    """Register actions from the configuration for Launcher"""

    module_name = os.environ["AVALON_CONFIG"]
    config = importlib.import_module(module_name)
    if not hasattr(config, "register_launcher_actions"):
        print(
            "Current configuration `%s` has no 'register_launcher_actions'"
            % config.__name__
        )
        return

    config.register_launcher_actions()


def register_environment_actions():
    """Register actions from AVALON_ACTIONS for Launcher."""

    paths = os.environ.get("AVALON_ACTIONS")
    if not paths:
        return

    for path in paths.split(os.pathsep):
        api.register_plugin_path(api.Action, path)

        # Run "register" if found.
        for module in lib.modules_from_path(path):
            if "register" not in dir(module):
                continue

            try:
                module.register()
            except Exception as e:
                print(
                    "Register method in {0} failed: {1}".format(
                        module, str(e)
                    )
                )
