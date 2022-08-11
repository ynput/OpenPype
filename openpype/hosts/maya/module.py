import os
from openpype.modules import OpenPypeModule
from openpype.modules.interfaces import IHostModule

MAYA_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class OpenPypeMaya(OpenPypeModule, IHostModule):
    name = "openpype_maya"
    host_name = "maya"

    def initialize(self, module_settings):
        self.enabled = True

    def add_implementation_envs(self, env, _app):
        # Add requirements to PYTHONPATH
        new_python_paths = [
            os.path.join(MAYA_ROOT_DIR, "startup")
        ]
        old_python_path = env.get("PYTHONPATH") or ""
        for path in old_python_path.split(os.pathsep):
            if not path:
                continue

            norm_path = os.path.normpath(path)
            if norm_path not in new_python_paths:
                new_python_paths.append(norm_path)

        env["PYTHONPATH"] = os.pathsep.join(new_python_paths)

        # Set default values if are not already set via settings
        defaults = {
            "OPENPYPE_LOG_NO_COLORS": "Yes"
        }
        for key, value in defaults.items():
            if not env.get(key):
                env[key] = value

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [
            os.path.join(MAYA_ROOT_DIR, "hooks")
        ]
