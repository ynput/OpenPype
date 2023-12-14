import os

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
        hooks_folder_path = os.path.dirname(os.path.realpath(__file__))
        custom_script_folder = os.path.join(os.path.dirname(hooks_folder_path), "blender_addon/startup/custom_scripts")
        blender_addons_folder = os.path.join(os.path.dirname(hooks_folder_path), "blender_addon/addons")
        self.log.warning(blender_addons_folder)
        self.launch_context.data.setdefault("python_scripts", []).append(
            os.path.join(custom_script_folder, self.script_file_name)
        )
        self.launch_context.data.setdefault("script_args", []).extend(
            [
                '--blender-addons-folder',
                blender_addons_folder
            ]
        )
