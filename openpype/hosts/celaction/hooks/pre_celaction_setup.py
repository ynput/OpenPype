import os
import shutil
import subprocess
import winreg
from openpype.lib import PreLaunchHook, get_openpype_execute_args
from openpype.hosts.celaction import api as caapi

CELACTION_API_DIR = os.path.dirname(
    os.path.abspath(caapi.__file__)
)


class CelactionPrelaunchHook(PreLaunchHook):
    """
    Bootstrap celacion with pype
    """
    workfile_ext = "scn"
    app_groups = ["celaction"]
    platforms = ["windows"]

    def execute(self):
        # Add workfile path to launch arguments
        workfile_path = self.workfile_path()
        if workfile_path:
            self.launch_context.launch_args.append(workfile_path)

        # setting output parameters
        path_user_settings = "\\".join([
            "Software", "CelAction", "CelAction2D", "User Settings"
        ])
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, path_user_settings)
        hKey = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, path_user_settings, 0,
            winreg.KEY_ALL_ACCESS
        )

        path_to_cli = os.path.join(CELACTION_API_DIR, "cli.py")
        subproces_args = get_openpype_execute_args("run", path_to_cli)
        openpype_executables = subproces_args.pop(0)

        winreg.SetValueEx(
            hKey,
            "SubmitAppTitle",
            0,
            winreg.REG_SZ,
            openpype_executables
        )

        parameters = subproces_args + [
            "--currentFile \\\"\"*SCENE*\"\\\"",
            "--chunk 10",
            "--frameStart *START*",
            "--frameEnd *END*",
            "--resolutionWidth *X*",
            "--resolutionHeight *Y*",
        ]
        winreg.SetValueEx(
            hKey, "SubmitParametersTitle", 0, winreg.REG_SZ,
            " ".join(parameters)
        )

        # setting resolution parameters
        path_submit = "\\".join([
            path_user_settings, "Dialogs", "SubmitOutput"
        ])
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, path_submit)
        hKey = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, path_submit, 0,
            winreg.KEY_ALL_ACCESS
        )
        winreg.SetValueEx(hKey, "SaveScene", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(hKey, "CustomX", 0, winreg.REG_DWORD, 1920)
        winreg.SetValueEx(hKey, "CustomY", 0, winreg.REG_DWORD, 1080)

        # making sure message dialogs don't appear when overwriting
        path_overwrite_scene = "\\".join([
            path_user_settings, "Messages", "OverwriteScene"
        ])
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, path_overwrite_scene)
        hKey = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, path_overwrite_scene, 0,
            winreg.KEY_ALL_ACCESS
        )
        winreg.SetValueEx(hKey, "Result", 0, winreg.REG_DWORD, 6)
        winreg.SetValueEx(hKey, "Valid", 0, winreg.REG_DWORD, 1)

        # set scane as not saved
        path_scene_saved = "\\".join([
            path_user_settings, "Messages", "SceneSaved"
        ])
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, path_scene_saved)
        hKey = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, path_scene_saved, 0,
            winreg.KEY_ALL_ACCESS
        )
        winreg.SetValueEx(hKey, "Result", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(hKey, "Valid", 0, winreg.REG_DWORD, 1)

    def workfile_path(self):
        workfile_path = self.data["last_workfile_path"]

        # copy workfile from template if doesnt exist any on path
        if not os.path.exists(workfile_path):
            # TODO add ability to set different template workfile path via
            # settings
            openpype_celaction_dir = os.path.dirname(CELACTION_API_DIR)
            template_path = os.path.join(
                openpype_celaction_dir,
                "resources",
                "celaction_template_scene.scn"
            )

            if not os.path.exists(template_path):
                self.log.warning(
                    "Couldn't find workfile template file in {}".format(
                        template_path
                    )
                )
                return

            self.log.info(
                f"Creating workfile from template: \"{template_path}\""
            )

            # Copy template workfile to new destinantion
            shutil.copy2(
                os.path.normpath(template_path),
                os.path.normpath(workfile_path)
            )

        self.log.info(f"Workfile to open: \"{workfile_path}\"")

        return workfile_path
