import os
import json
import tempfile
import contextlib
import socket
from pprint import pformat

from openpype.lib import (
    PreLaunchHook,
    get_openpype_username,
    run_subprocess,
)
from openpype.lib.applications import (
    ApplicationLaunchFailed
)
from openpype.hosts import flame as opflame


class FlamePrelaunch(PreLaunchHook):
    """ Flame prelaunch hook

    Will make sure flame_script_dirs are copied to user's folder defined
    in environment var FLAME_SCRIPT_DIR.
    """
    app_groups = ["flame"]
    permissions = 0o777

    wtc_script_path = os.path.join(
        opflame.HOST_DIR, "api", "scripts", "wiretap_com.py")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signature = "( {} )".format(self.__class__.__name__)

    def execute(self):
        _env = self.launch_context.env
        self.flame_python_exe = _env["OPENPYPE_FLAME_PYTHON_EXEC"]
        self.flame_pythonpath = _env["OPENPYPE_FLAME_PYTHONPATH"]

        """Hook entry method."""
        project_doc = self.data["project_doc"]
        project_name = project_doc["name"]
        volume_name = _env.get("FLAME_WIRETAP_VOLUME")

        # get image io
        project_settings = self.data["project_settings"]

        imageio_flame = project_settings["flame"]["imageio"]

        # Check whether 'enabled' key from host imageio settings exists
        # so we can tell if host is using the new colormanagement framework.
        # If the 'enabled' isn't found we want 'colormanaged' set to True
        # because prior to the key existing we always did colormanagement for
        # Flame
        colormanaged = imageio_flame.get("enabled")
        # if key was not found, set to True
        # ensuring backward compatibility
        if colormanaged is None:
            colormanaged = True

        # get user name and host name
        user_name = get_openpype_username()
        user_name = user_name.replace(".", "_")

        hostname = socket.gethostname()  # not returning wiretap host name

        self.log.debug("Collected user \"{}\"".format(user_name))
        self.log.info(pformat(project_doc))
        _db_p_data = project_doc["data"]
        width = _db_p_data["resolutionWidth"]
        height = _db_p_data["resolutionHeight"]
        fps = float(_db_p_data["fps"])

        project_data = {
            "Name": project_doc["name"],
            "Nickname": _db_p_data["code"],
            "Description": "Created by OpenPype",
            "SetupDir": project_doc["name"],
            "FrameWidth": int(width),
            "FrameHeight": int(height),
            "AspectRatio": float((width / height) * _db_p_data["pixelAspect"]),
            "FrameRate": self._get_flame_fps(fps)
        }

        data_to_script = {
            # from settings
            "host_name": _env.get("FLAME_WIRETAP_HOSTNAME") or hostname,
            "volume_name": volume_name,
            "group_name": _env.get("FLAME_WIRETAP_GROUP"),

            # from project
            "project_name": project_name,
            "user_name": user_name,
            "project_data": project_data
        }

        # add color management data
        if colormanaged:
            project_data.update({
                "FrameDepth": str(imageio_flame["project"]["frameDepth"]),
                "FieldDominance": str(
                    imageio_flame["project"]["fieldDominance"])
            })
            data_to_script["color_policy"] = str(
                imageio_flame["project"]["colourPolicy"])

        self.log.info(pformat(dict(_env)))
        self.log.info(pformat(data_to_script))

        # add to python path from settings
        self._add_pythonpath()

        app_arguments = self._get_launch_arguments(data_to_script)

        # fix project data permission issue
        self._fix_permissions(project_name, volume_name)

        self.launch_context.launch_args.extend(app_arguments)

    def _fix_permissions(self, project_name, volume_name):
        """Work around for project data permissions

        Reported issue: when project is created locally on one machine,
        it is impossible to migrate it to other machine. Autodesk Flame
        is crating some unmanagable files which needs to be opened to 0o777.

        Args:
            project_name (str): project name
            volume_name (str): studio volume
        """
        dirs_to_modify = [
            "/usr/discreet/project/{}".format(project_name),
            "/opt/Autodesk/clip/{}/{}.prj".format(volume_name, project_name),
            "/usr/discreet/clip/{}/{}.prj".format(volume_name, project_name)
        ]

        for dirtm in dirs_to_modify:
            for root, dirs, files in os.walk(dirtm):
                try:
                    for name in set(dirs) | set(files):
                        path = os.path.join(root, name)
                        st = os.stat(path)
                        if oct(st.st_mode) != self.permissions:
                            os.chmod(path, self.permissions)

                except OSError as exc:
                    self.log.warning("Not able to open files: {}".format(exc))

    def _get_flame_fps(self, fps_num):
        fps_table = {
            float(23.976): "23.976 fps",
            int(25): "25 fps",
            int(24): "24 fps",
            float(29.97): "29.97 fps DF",
            int(30): "30 fps",
            int(50): "50 fps",
            float(59.94): "59.94 fps DF",
            int(60): "60 fps"
        }

        match_key = min(fps_table.keys(), key=lambda x: abs(x - fps_num))

        try:
            return fps_table[match_key]
        except KeyError as msg:
            raise KeyError((
                "Missing FPS key in conversion table. "
                "Following keys are available: {}".format(fps_table.keys())
            )) from msg

    def _add_pythonpath(self):
        pythonpath = self.launch_context.env.get("PYTHONPATH")

        # separate it explicitly by `;` that is what we use in settings
        new_pythonpath = self.flame_pythonpath.split(os.pathsep)
        new_pythonpath += pythonpath.split(os.pathsep)

        self.launch_context.env["PYTHONPATH"] = os.pathsep.join(new_pythonpath)

    def _get_launch_arguments(self, script_data):
        # Dump data to string
        dumped_script_data = json.dumps(script_data)

        with make_temp_file(dumped_script_data) as tmp_json_path:
            # Prepare subprocess arguments
            args = [
                self.flame_python_exe.format(
                    **self.launch_context.env
                ),
                self.wtc_script_path,
                tmp_json_path
            ]
            self.log.info("Executing: {}".format(" ".join(args)))

            process_kwargs = {
                "logger": self.log,
                "env": self.launch_context.env
            }

            run_subprocess(args, **process_kwargs)

            # process returned json file to pass launch args
            return_json_data = open(tmp_json_path).read()
            returned_data = json.loads(return_json_data)
            app_args = returned_data.get("app_args")
            self.log.info("____ app_args: `{}`".format(app_args))

            if not app_args:
                RuntimeError("App arguments were not solved")

        return app_args


@contextlib.contextmanager
def make_temp_file(data):
    try:
        # Store dumped json to temporary file
        temporary_json_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        temporary_json_file.write(data)
        temporary_json_file.close()
        temporary_json_filepath = temporary_json_file.name.replace(
            "\\", "/"
        )

        yield temporary_json_filepath

    except IOError as _error:
        raise IOError(
            "Not able to create temp json file: {}".format(
                _error
            )
        )

    finally:
        # Remove the temporary json
        os.remove(temporary_json_filepath)
