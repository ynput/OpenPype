import os
import shutil
import winreg
import subprocess
from openpype.lib import PreLaunchHook, get_openpype_execute_args
from openpype.hosts.celaction import scripts

CELACTION_SCRIPTS_DIR = os.path.dirname(
    os.path.abspath(scripts.__file__)
)


class CelactionPrelaunchHook(PreLaunchHook):
    """
    Bootstrap celacion with pype
    """
    app_groups = ["celaction"]
    platforms = ["windows"]

    def execute(self):
        asset_doc = self.data["asset_doc"]
        width = asset_doc["data"]["resolutionWidth"]
        height = asset_doc["data"]["resolutionHeight"]

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

        path_to_cli = os.path.join(CELACTION_SCRIPTS_DIR, "publish_cli.py")
        subprocess_args = get_openpype_execute_args("run", path_to_cli)
        openpype_executable = subprocess_args.pop(0)
        workfile_settings = self.get_workfile_settings()

        winreg.SetValueEx(
            hKey,
            "SubmitAppTitle",
            0,
            winreg.REG_SZ,
            openpype_executable
        )

        # add required arguments for workfile path
        parameters = subprocess_args + [
            "--currentFile", "*SCENE*"
        ]

        # Add custom parameters from workfile settings
        if "render_chunk" in workfile_settings["submission_overrides"]:
            parameters += [
                "--chunk", "*CHUNK*"
           ]
        if "resolution" in workfile_settings["submission_overrides"]:
            parameters += [
                "--resolutionWidth", "*X*",
                "--resolutionHeight", "*Y*"
            ]
        if "frame_range" in workfile_settings["submission_overrides"]:
            parameters += [
                "--frameStart", "*START*",
                "--frameEnd", "*END*"
            ]

        winreg.SetValueEx(
            hKey, "SubmitParametersTitle", 0, winreg.REG_SZ,
            subprocess.list2cmdline(parameters)
        )

        self.log.debug(f"__ parameters: \"{parameters}\"")

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
        winreg.SetValueEx(hKey, "CustomX", 0, winreg.REG_DWORD, width)
        winreg.SetValueEx(hKey, "CustomY", 0, winreg.REG_DWORD, height)

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
            openpype_celaction_dir = os.path.dirname(CELACTION_SCRIPTS_DIR)
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

    def get_workfile_settings(self):
        return self.data["project_settings"]["celaction"]["workfile"]
