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
    script_file_name = 'set_deadline_scene_properties.py'

    def get_formatted_outputs_paths(self):
        data = self.launch_context.data
        target_os = "linux"

        retrieved_work_dir = self._get_correct_work_dir(data, target_os)
        if not retrieved_work_dir:
            self.log.warning(f"Can't find correct work directory for os {target_os}. Can't set default output path.")
            return '/tmp/'

        sequence_name, shot_name = data['asset_name'].split('_')

        try:
            base_output_path = os.path.join(
                    retrieved_work_dir,
                    data['project_name'],
                    'Shots',
                    sequence_name,
                    data['asset_name'],
                    'publish',
                    'render',
                    f'render{data["task_name"]}Main'
                )
            render_layer_path = self._generate_path_with_version(
                base_output_path, data['project_name'], shot_name
            )
            output_path = self._generate_path_without_version(
                base_output_path, data['project_name'], shot_name
            )
            return render_layer_path, output_path

        except IndexError as err:
            self.log.warning("Value is missing from launch_context data. Can't set default output path.")
            self.log.warning(err)
            tempdir = tempfile.gettempdir(),
            return tempdir, tempdir

    def _get_correct_work_dir(self, data, given_os):
        work_directories = data['project_doc']['config']['roots']['work']
        retrieved_work_dir = None
        for retrieved_os, work_folder_path in work_directories.items():
            if given_os.lower().startswith(retrieved_os.lower()):
                retrieved_work_dir = work_folder_path
                break

        return retrieved_work_dir


    def _generate_path_with_version(self, base_path, project_name, shot_name):
        return os.path.join(
            base_path,
            '{render_layer_name}',
            '{version}',
            '_'.join([project_name, shot_name, '{render_layer_name}', '{version}'])
        )

    def _generate_path_without_version(self, base_path, project_name, shot_name):
        return os.path.join(
            base_path,
            '{render_layer_name}',
            '_'.join([project_name, shot_name, '{render_layer_name}'])
        )

    def execute(self):
        hooks_folder_path = os.path.dirname(os.path.realpath(__file__))
        custom_script_folder = os.path.join(os.path.dirname(hooks_folder_path), "blender_addon/startup/custom_scripts")

        self.launch_context.data.setdefault("python_scripts", []).append(
            os.path.join(custom_script_folder, self.script_file_name)
        )
        render_layer_path, output_path = self.get_formatted_outputs_paths()
        self.launch_context.data.setdefault("script_args", []).extend(
            [
                '--render-layer-path',
                render_layer_path,
                '--output-path',
                output_path

            ]
        )
