import logging
import os
import _winreg
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
        asset = env["AVALON_ASSET"]
        task = env["AVALON_TASK"]
        workdir = env["AVALON_WORKDIR"]
        project_name = f"{asset}_{task}"

        self.log.info(f"{self.signature}")

        os.makedirs(workdir, exist_ok=True)

        project_file = os.path.join(workdir, f"{project_name}.scn")
        env["PYPE_CELACTION_PROJECT_FILE"] = project_file

        ##########################
        # setting output parameters
        path = r"Software\CelAction\CelAction2D\User Settings"
        _winreg.CreateKey(_winreg.HKEY_CURRENT_USER, path)
        hKey = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,
                               r"Software\CelAction\CelAction2D\User Settings",
                               0, _winreg.KEY_ALL_ACCESS)

        # TODO: change to root path and pyblish standalone to premiere way
        root_path = os.getenv("PIPELINE_ROOT", os.path.dirname(__file__))
        path = os.path.join(root_path, "launchers", "pyblish_standalone.bat")

        _winreg.SetValueEx(hKey, "SubmitAppTitle", 0, _winreg.REG_SZ, path)

        parameters = " --path \"*SCENE*\" -d chunk *CHUNK* -d start *START*"
        parameters += " -d end *END* -d x *X* -d y *Y* -rh celaction"
        parameters += " -8 -d progpath \"*PROGPATH*\""
        _winreg.SetValueEx(hKey, "SubmitParametersTitle", 0, _winreg.REG_SZ,
                           parameters)

        # setting resolution parameters
        path = r"Software\CelAction\CelAction2D\User Settings\Dialogs"
        path += r"\SubmitOutput"
        _winreg.CreateKey(_winreg.HKEY_CURRENT_USER, path)
        hKey = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, path, 0,
                               _winreg.KEY_ALL_ACCESS)
        _winreg.SetValueEx(hKey, "SaveScene", 0, _winreg.REG_DWORD, 1)
        _winreg.SetValueEx(hKey, "CustomX", 0, _winreg.REG_DWORD, 1920)
        _winreg.SetValueEx(hKey, "CustomY", 0, _winreg.REG_DWORD, 1080)

        # making sure message dialogs don't appear when overwriting
        path = r"Software\CelAction\CelAction2D\User Settings\Messages"
        path += r"\OverwriteScene"
        _winreg.CreateKey(_winreg.HKEY_CURRENT_USER, path)
        hKey = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, path, 0,
                               _winreg.KEY_ALL_ACCESS)
        _winreg.SetValueEx(hKey, "Result", 0, _winreg.REG_DWORD, 6)
        _winreg.SetValueEx(hKey, "Valid", 0, _winreg.REG_DWORD, 1)

        path = r"Software\CelAction\CelAction2D\User Settings\Messages"
        path += r"\SceneSaved"
        _winreg.CreateKey(_winreg.HKEY_CURRENT_USER, path)
        hKey = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, path, 0,
                               _winreg.KEY_ALL_ACCESS)
        _winreg.SetValueEx(hKey, "Result", 0, _winreg.REG_DWORD, 1)
        _winreg.SetValueEx(hKey, "Valid", 0, _winreg.REG_DWORD, 1)

        return True
