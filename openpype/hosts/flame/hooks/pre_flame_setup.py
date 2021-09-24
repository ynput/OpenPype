import os
import json
import tempfile
from openpype.lib import PreLaunchHook
from openpype.hosts import flame as opflame
import openpype

from pprint import pformat


class FlamePrelaunch(PreLaunchHook):
    """ Flame prelaunch hook

    Will make sure flame_script_dirs are coppied to user's folder defined
    in environment var FLAME_SCRIPT_DIR.
    """
    app_groups = ["flame"]

    # todo: replace version number with avalon launch app version
    flame_python_exe = "/opt/Autodesk/python/2021/bin/python2.7"

    wtc_script_path = os.path.join(
        opflame.HOST_DIR, "sripts", "wiretap_com.py")

    def execute(self):
        data_to_script = {
            "project_name": "test_project_325",
            "user_name": "jakub_jeza_jezek"
        }

        app_arguments = self._get_launch_arguments(data_to_script)

        self.log.info(pformat(dict(self.launch_context.env)))

        opflame.setup(self.launch_context.env)

        self.launch_context.launch_args.extend(app_arguments)

    def _get_launch_arguments(self, script_data):
        # Dump data to string
        dumped_script_data = json.dumps(script_data)

        # Store dumped json to temporary file
        temporary_json_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        temporary_json_file.write(dumped_script_data)
        temporary_json_file.close()
        temporary_json_filepath = temporary_json_file.name.replace(
            "\\", "/"
        )

        # Prepare subprocess arguments
        args = list(self.flame_python_exe)
        args.append(self.wtc_script_path)
        args.append(temporary_json_filepath)
        self.log.debug("Executing: {}".format(" ".join(args)))

        # Run burnin script
        process_kwargs = {
            "logger": self.log,
            "env": {}
        }

        openpype.api.run_subprocess(args, **process_kwargs)

        returned_data = json.loads(temporary_json_filepath)

        app_args = returned_data.get("app_args")

        if not app_args:
            RuntimeError("App arguments were not solved")
        else:
            # Remove the temporary json
            os.remove(temporary_json_filepath)

        return app_args
