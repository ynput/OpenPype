import logging
import os
import winreg
from pype.lib import PypeHook
from pype.api import get_last_version_from_path
from pypeapp import Anatomy, Logger

from avalon import io, api, lib

log = logging.getLogger(__name__)


class CelactionPrelaunchHook(PypeHook):
    """
    This hook will check if current workfile path has Unreal
    project inside. IF not, it initialize it and finally it pass
    path to the project by environment variable to Unreal launcher
    shell script.
    """
    workfile_ext = "scn"

    def __init__(self, logger=None):
        if not logger:
            self.log = Logger().get_logger(self.__class__.__name__)
        else:
            self.log = logger

        self.signature = "( {} )".format(self.__class__.__name__)

    def execute(self, *args, env: dict = None) -> bool:
        if not env:
            self.env = os.environ
        else:
            self.env = env

        self._S = api.Session
        project = self._S["AVALON_PROJECT"] = self.env["AVALON_PROJECT"]
        asset = self._S["AVALON_ASSET"] = self.env["AVALON_ASSET"]
        task = self._S["AVALON_TASK"] = self.env["AVALON_TASK"]
        workdir = self._S["AVALON_WORKDIR"] = self.env["AVALON_WORKDIR"]

        anatomy_filled = self.get_anatomy_filled()

        app = "celaction_publish"
        workfile = anatomy_filled["work"]["file"]
        version = anatomy_filled["version"]

        os.makedirs(workdir, exist_ok=True)
        self.log.info(f"Work dir is: `{workdir}`")

        # get last version if any
        workfile_last = get_last_version_from_path(
            workdir, workfile.split(version))

        if workfile_last:
            workfile = workfile_last

        project_file = os.path.join(workdir, workfile)
        env["PYPE_CELACTION_PROJECT_FILE"] = project_file

        self.log.info(f"Workfile is: `{project_file}`")

        ##########################
        # setting output parameters
        path = r"Software\CelAction\CelAction2D\User Settings"
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, path)
        hKey = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            "Software\\CelAction\\CelAction2D\\User Settings", 0,
            winreg.KEY_ALL_ACCESS)

        # TODO: change to root path and pyblish standalone to premiere way
        pype_root_path = os.getenv("PYPE_ROOT")
        path = os.path.join(pype_root_path,
                            "pype.bat")

        winreg.SetValueEx(hKey, "SubmitAppTitle", 0, winreg.REG_SZ, path)

        parameters = [
            "launch",
            f"--app {app}",
            f"--project {project}",
            f"--asset {asset}",
            f"--task {task}",
            "--currentFile \"*SCENE*\"",
            "--chunk *CHUNK*",
            "--frameStart *START*",
            "--frameEnd *END*",
            "--resolutionWidth *X*",
            "--resolutionHeight *Y*",
            # "--programDir \"'*PROGPATH*'\""
        ]
        winreg.SetValueEx(hKey, "SubmitParametersTitle", 0, winreg.REG_SZ,
                          " ".join(parameters))

        # setting resolution parameters
        path = r"Software\CelAction\CelAction2D\User Settings\Dialogs"
        path += r"\SubmitOutput"
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, path)
        hKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0,
                              winreg.KEY_ALL_ACCESS)
        winreg.SetValueEx(hKey, "SaveScene", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(hKey, "CustomX", 0, winreg.REG_DWORD, 1920)
        winreg.SetValueEx(hKey, "CustomY", 0, winreg.REG_DWORD, 1080)

        # making sure message dialogs don't appear when overwriting
        path = r"Software\CelAction\CelAction2D\User Settings\Messages"
        path += r"\OverwriteScene"
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, path)
        hKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0,
                              winreg.KEY_ALL_ACCESS)
        winreg.SetValueEx(hKey, "Result", 0, winreg.REG_DWORD, 6)
        winreg.SetValueEx(hKey, "Valid", 0, winreg.REG_DWORD, 1)

        path = r"Software\CelAction\CelAction2D\User Settings\Messages"
        path += r"\SceneSaved"
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, path)
        hKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0,
                              winreg.KEY_ALL_ACCESS)
        winreg.SetValueEx(hKey, "Result", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(hKey, "Valid", 0, winreg.REG_DWORD, 1)

        return True

    def get_anatomy_filled(self):
        root_path = api.registered_root()
        project_name = self._S["AVALON_PROJECT"]
        asset_name = self._S["AVALON_ASSET"]

        io.install()
        project_entity = io.find_one({
            "type": "project",
            "name": project_name
        })
        assert project_entity, (
            "Project '{0}' was not found."
        ).format(project_name)
        log.debug("Collected Project \"{}\"".format(project_entity))

        asset_entity = io.find_one({
            "type": "asset",
            "name": asset_name,
            "parent": project_entity["_id"]
        })
        assert asset_entity, (
            "No asset found by the name '{0}' in project '{1}'"
        ).format(asset_name, project_name)

        project_name = project_entity["name"]

        log.info(
            "Anatomy object collected for project \"{}\".".format(project_name)
        )

        hierarchy_items = asset_entity["data"]["parents"]
        hierarchy = ""
        if hierarchy_items:
            hierarchy = os.path.join(*hierarchy_items)

        template_data = {
            "root": root_path,
            "project": {
                "name": project_name,
                "code": project_entity["data"].get("code")
            },
            "asset": asset_entity["name"],
            "hierarchy": hierarchy.replace("\\", "/"),
            "task": self._S["AVALON_TASK"],
            "ext": self.workfile_ext,
            "version": 1,
            "username": os.getenv("PYPE_USERNAME", "").strip()
        }

        avalon_app_name = os.environ.get("AVALON_APP_NAME")
        if avalon_app_name:
            application_def = lib.get_application(avalon_app_name)
            app_dir = application_def.get("application_dir")
            if app_dir:
                template_data["app"] = app_dir

        anatomy = Anatomy(project_name)
        anatomy_filled = anatomy.format_all(template_data).get_solved()

        return anatomy_filled
