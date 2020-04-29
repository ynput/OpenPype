import logging
import os
import winreg
from pype.lib import PypeHook
from pypeapp import Logger

log = logging.getLogger(__name__)


class CelactionPrelaunchHook(PypeHook):
    """
    This hook will check if current workfile path has Unreal
    project inside. IF not, it initialize it and finally it pass
    path to the project by environment variable to Unreal launcher
    shell script.
    """

    def __init__(self, logger=None):
        if not logger:
            self.log = Logger().get_logger(self.__class__.__name__)
        else:
            self.log = logger

        self.signature = "( {} )".format(self.__class__.__name__)

    def execute(self, *args, env: dict = None) -> bool:
        if not env:
            env = os.environ
        project = env["AVALON_PROJECT"]
        asset = env["AVALON_ASSET"]
        task = env["AVALON_TASK"]
        app = "pype_publish_standalone"
        workdir = env["AVALON_WORKDIR"]
        project_name = f"{asset}_{task}"
        version = "v001"

        self.log.info(f"{self.signature}")

        os.makedirs(workdir, exist_ok=True)
        self.log.info(f"Work dir is: `{workdir}`")

        project_file = os.path.join(workdir, f"{project_name}_{version}.scn")
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
            "--resolutionWide *X*",
            "--resolutionHeight *Y*",
            "--registerHost celaction",
            "-8",
            "--programPath \"\'*PROGPATH*\'\""
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
