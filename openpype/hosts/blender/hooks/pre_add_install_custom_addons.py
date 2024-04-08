from pathlib import Path

from openpype.hosts.blender.hooks import pre_add_run_python_script_arg
from openpype.lib import PreLaunchHook


class InstallCustomAddons(PreLaunchHook):
    """Detect and append all custom scripts from
    blender_addon/startup/custom_scripts to Blender execution command.
    """

    order = pre_add_run_python_script_arg.AddPythonScriptToLaunchArgs.order - 1
    app_groups = [
        "blender",
    ]
    script_file_name = 'install_custom_addons.py'

    def execute(self):
        hooks_folder_path = Path(__file__).parent
        custom_script_folder = hooks_folder_path.parent.joinpath("blender_addon", "startup", "custom_scripts")
        blender_addons_folder = hooks_folder_path.parent.joinpath("blender_addon", "addons")

        script_file = custom_script_folder.joinpath(self.script_file_name)
        if not script_file.exists() or not script_file.is_file():
            raise FileNotFoundError(f"Can't find {self.script_file_name} in {custom_script_folder}.")

        self.launch_context.data.setdefault("python_scripts", []).append(
            custom_script_folder.joinpath(self.script_file_name)
        )
        self.launch_context.data.setdefault("script_args", []).extend(
            [
                '--blender-addons-folder',
                str(blender_addons_folder)
            ]
        )
