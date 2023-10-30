import os
from openpype.modules import OpenPypeModule, IHostAddon

HOUDINI_HOST_DIR = os.path.dirname(os.path.abspath(__file__))


def merge_paths(*paths):
    """Merge path strings to a single uniqified `os.pathsep` joined string.

    Each path argument can itself be `os.pathsep` joined string.
    >>> merge_paths("A", "A;B;C", "D;E")
    "A;B;C;D;E"


    """
    result = []
    processed = set()
    for paths_str in paths:
        for path in paths_str.split(os.pathsep):
            if not path:
                continue

            path = os.path.normpath(path)
            if path in processed:
                continue

            result.append(path)
            processed.add(path)

    return os.pathsep.join(result)


class HoudiniAddon(OpenPypeModule, IHostAddon):
    name = "houdini"
    host_name = "houdini"

    def initialize(self, module_settings):
        self.enabled = True

    def add_implementation_envs(self, env, _app):
        # Add requirements to HOUDINI_PATH, HOUDINI_MENU_PATH, HOUDINI_OTL_PATH
        startup_path = os.path.join(HOUDINI_HOST_DIR, "startup")
        resources_path = os.path.join(HOUDINI_HOST_DIR, "resources")

        # Add ampersand for unknown reason (Maybe is needed in Houdini?)
        env["HOUDINI_PATH"] = merge_paths(
            startup_path, env.get("HOUDINI_PATH", ""), "&"
        )
        env["HOUDINI_MENU_PATH"] = merge_paths(
            startup_path, env.get("HOUDINI_MENU_PATH", ""), "&"
        )
        env["HOUDINI_OTL_PATH"] = merge_paths(
            resources_path, env.get("HOUDINI_OTL_PATH", ""), "&"
        )

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [
            os.path.join(HOUDINI_HOST_DIR, "hooks")
        ]

    def get_workfile_extensions(self):
        return [".hip", ".hiplc", ".hipnc"]
