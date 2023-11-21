import os

from openpype.hosts.blender.hooks import pre_add_run_python_script_arg
from openpype.lib import PreLaunchHook


class InstallDeadlineAddon(PreLaunchHook):
    """Add python script to be executed before Blender launch."""

    order = pre_add_run_python_script_arg.AddPythonScriptToLaunchArgs.order - 1
    app_groups = [
        "blender",
    ]

    def execute(self):
        print('\n#####\n#####')
        print(self.launch_context)
        print(self.launch_context.launch_args)
        print(self.launch_context.data)
        print('\n#####\n#####')
        file_directory = os.path.dirname(os.path.realpath(__file__))
        addon_path = os.path.join(file_directory, "../blender_addon/startup/install_deadline_addon.py")
        #addon_path = "C:/Users/dev/quad/OpenPype/openpype/hosts/blender/blender_addon/startup/install_deadline_addon.py"
        self.launch_context.data.setdefault("python_scripts", []).append(addon_path)
