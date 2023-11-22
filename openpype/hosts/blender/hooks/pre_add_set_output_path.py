import os
import tempfile

from openpype.hosts.blender.hooks import pre_add_run_python_script_arg
from openpype.lib import PreLaunchHook


class InstallDeadlineAddon(PreLaunchHook):
    """Detect and append all custom scripts from
    blender_addon/startup/custom_scripts to Blender execution command.
    """

    order = pre_add_run_python_script_arg.AddPythonScriptToLaunchArgs.order - 1
    app_groups = [
        "blender",
    ]
    script_file_name = 'set_output_path.py'

    def get_formatted_format_path(self):
        data = self.launch_context.data
        current_os = data['env']['OS']

        retrieved_work_dir = self._get_correct_work_dir(data, current_os)
        if not retrieved_work_dir:
            self.log.warning(f"Can't find correct work directory for os {current_os}. Can't set default output path.")
            return self.get_temporary_file_path()

        sequence_name, shot_name = data['asset_name'].split('_')
        version = 'v001'
        render_layer = 'renderLayer'
        try:
            return os.path.join(
                retrieved_work_dir,
                data['project_name'],
                'Shots',
                sequence_name,
                data['asset_name'],
                'publish',
                'render',
                render_layer,
                version,
                '_'.join([data['project_name'], shot_name, version])
            )
        except IndexError as err:
            self.log.warning("Value is missing from launch_context data. Can't set default output path.")
            self.log.warning(err)
            return self.get_temporary_file_path()

    def _get_correct_work_dir(self, data, given_os):
        work_directories = data['project_doc']['config']['roots']['work']
        retrieved_work_dir = None
        for retrieved_os, work_folder_path in work_directories.items():
            if given_os.lower().startswith(retrieved_os.lower()):
                retrieved_work_dir = work_folder_path
                break

        return retrieved_work_dir

    def get_temporary_file_path(self):
        return os.path.join(tempfile.gettempdir(), '####')

    def execute(self):
        hooks_folder_path = os.path.dirname(os.path.realpath(__file__))
        custom_script_folder = os.path.join(os.path.dirname(hooks_folder_path), "blender_addon/startup/custom_scripts")

        self.launch_context.data.setdefault("python_scripts", []).append(
            os.path.join(custom_script_folder, self.script_file_name)
        )
        self.launch_context.data.setdefault("script_args", []).extend(
            [
                '--output-path',
                self.get_formatted_format_path()
            ]
        )
