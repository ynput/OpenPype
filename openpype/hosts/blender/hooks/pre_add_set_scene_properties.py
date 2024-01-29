from pathlib import Path
import tempfile

from openpype.hosts.blender.hooks import pre_add_run_python_script_arg
from openpype.lib import PreLaunchHook


class SetSceneProperties(PreLaunchHook):
    """Set required scene data for custom scripts
    """

    order = pre_add_run_python_script_arg.AddPythonScriptToLaunchArgs.order - 1
    app_groups = [
        "blender",
    ]
    script_file_name = 'set_scene_properties.py'

    def get_formatted_outputs_paths(self):
        data = self.launch_context.data

        # This value is hardcoded because the farm's workers are based on Linux.
        # In the future there should be a way to get this info somewhere.
        target_os = "linux"
        current_os = data['env']['OS']
        hierarchy = data['workdir_data']['hierarchy']
        entity_name = data['asset_name']

        target_work_dir = self._get_correct_work_dir(data, target_os)
        current_work_dir = self._get_correct_work_dir(data, current_os)
        if not target_work_dir:
            self.log.warning(f"Can't find correct work directory for os {target_os}. Can't set default output path.")
            return '/tmp/'

        if not current_work_dir:
            self.log.warning(f"Can't find correct work directory for os {current_work_dir}. Can't set default output path.")
            return '/tmp/'

        try:
            base_output_path = Path(
                    data['project_name'],
                    hierarchy,
                    entity_name,
                    'publish',
                    'render',
                )
            render_layer_path = self._generate_path_with_version(
                target_work_dir, base_output_path, data['project_name'], entity_name
            )
            output_path = self._generate_path_without_version(
                current_work_dir, base_output_path, data['project_name'], entity_name
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


    def _generate_path_with_version(self, work_dir, base_path, project_name, entity_name):
        return Path(
            work_dir,
            base_path,
            '{version}',
            '{render_layer_name}',
            '_'.join([project_name, entity_name, '{render_layer_name}', '{version}'])
        )

    def _generate_path_without_version(self, work_dir, base_path, project_name, entity_name):
        return Path(
            work_dir,
            base_path,
            '{render_layer_name}',
            '_'.join([project_name, entity_name, '{render_layer_name}'])
        )

    def execute(self):
        hooks_folder_path = Path(__file__).parent
        custom_script_folder = hooks_folder_path.parent.joinpath("blender_addon", "startup", "custom_scripts")

        script_file = custom_script_folder.joinpath(self.script_file_name)
        if not script_file.exists() or not script_file.is_file():
            raise FileNotFoundError(f"Can't find {self.script_file_name} in {custom_script_folder}.")

        self.launch_context.data.setdefault("python_scripts", []).append(
            custom_script_folder.joinpath(self.script_file_name)
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
