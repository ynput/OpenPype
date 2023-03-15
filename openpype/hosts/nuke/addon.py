import os
import platform
from openpype.modules import OpenPypeModule, IHostAddon

NUKE_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class NukeAddon(OpenPypeModule, IHostAddon):
    name = "nuke"
    host_name = "nuke"

    def initialize(self, module_settings):
        self.enabled = True

    def add_implementation_envs(self, env, _app):
        # Add requirements to NUKE_PATH
        new_nuke_paths = [
            os.path.join(NUKE_ROOT_DIR, "startup")
        ]
        old_nuke_path = env.get("NUKE_PATH") or ""
        for path in old_nuke_path.split(os.pathsep):
            if not path:
                continue

            norm_path = os.path.normpath(path)
            if norm_path not in new_nuke_paths:
                new_nuke_paths.append(norm_path)

        env["NUKE_PATH"] = os.pathsep.join(new_nuke_paths)
        # Remove auto screen scale factor for Qt
        # - let Nuke decide it's value
        env.pop("QT_AUTO_SCREEN_SCALE_FACTOR", None)
        # Remove tkinter library paths if are set
        env.pop("TK_LIBRARY", None)
        env.pop("TCL_LIBRARY", None)

        # Add vendor to PYTHONPATH
        python_path = env["PYTHONPATH"]
        python_path_parts = []
        if python_path:
            python_path_parts = python_path.split(os.pathsep)
        vendor_path = os.path.join(NUKE_ROOT_DIR, "vendor")
        python_path_parts.insert(0, vendor_path)
        env["PYTHONPATH"] = os.pathsep.join(python_path_parts)

        # Set default values if are not already set via settings
        defaults = {
            "LOGLEVEL": "DEBUG"
        }
        for key, value in defaults.items():
            if not env.get(key):
                env[key] = value

        # Try to add QuickTime to PATH
        quick_time_path = "C:/Program Files (x86)/QuickTime/QTSystem"
        if platform.system() == "windows" and os.path.exists(quick_time_path):
            path_value = env.get("PATH") or ""
            path_paths = [
                path
                for path in path_value.split(os.pathsep)
                if path
            ]
            path_paths.append(quick_time_path)
            env["PATH"] = os.pathsep.join(path_paths)

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [
            os.path.join(NUKE_ROOT_DIR, "hooks")
        ]

    def get_workfile_extensions(self):
        return [".nk"]
