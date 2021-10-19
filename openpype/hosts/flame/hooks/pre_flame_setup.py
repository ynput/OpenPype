import os
import json
import tempfile
from openpype.lib import (
    PreLaunchHook, get_openpype_username)
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
        opflame.HOST_DIR, "scripts", "wiretap_com.py")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.signature = "( {} )".format(self.__class__.__name__)

    def execute(self):
        """Hook entry method."""
        project_doc = self.data["project_doc"]
        user_name = get_openpype_username()

        self.log.debug("Collected user \"{}\"".format(user_name))
        self.log.info(pformat(project_doc))
        _db_p_data = project_doc["data"]
        width = _db_p_data["resolutionWidth"]
        height = _db_p_data["resolutionHeight"]
        fps = int(_db_p_data["fps"])

        project_data = {
            "Name": project_doc["name"],
            "Nickname": _db_p_data["code"],
            "Description": "Created by OpenPype",
            "SetupDir": project_doc["name"],
            "FrameWidth": int(width),
            "FrameHeight": int(height),
            "AspectRatio": float((width / height) * _db_p_data["pixelAspect"]),
            "FrameRate": "{} fps".format(fps),
            "FrameDepth": "16-bit fp",
            "FieldDominance": "PROGRESSIVE"
        }

        data_to_script = {
            # from settings
            "host_name": "localhost",
            "volume_name": "stonefs",
            "group_name": "staff",
            "color_policy": "ACES 1.1",

            # from project
            "project_name": project_doc["name"],
            "user_name": user_name,
            "project_data": project_data
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
        args = [
            self.flame_python_exe,
            self.wtc_script_path,
            temporary_json_filepath
        ]
        self.log.info("Executing: {}".format(" ".join(args)))

        process_kwargs = {
            "logger": self.log,
            "env": {}
        }

        openpype.api.run_subprocess(args, **process_kwargs)

        # process returned json file to pass launch args
        return_json_data = open(temporary_json_filepath).read()
        returned_data = json.loads(return_json_data)
        app_args = returned_data.get("app_args")
        self.log.info("____ app_args: `{}`".format(app_args))

        if not app_args:
            RuntimeError("App arguments were not solved")

        # Remove the temporary json
        os.remove(temporary_json_filepath)

        return app_args
