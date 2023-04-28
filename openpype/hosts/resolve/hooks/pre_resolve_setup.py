import os
from pathlib import Path
import platform
from openpype.lib import PreLaunchHook
from openpype.hosts.resolve.utils import setup


class ResolvePrelaunch(PreLaunchHook):
    """
    This hook will check if current workfile path has Resolve
    project inside. IF not, it initialize it and finally it pass
    path to the project by environment variable to Premiere launcher
    shell script.
    """
    app_groups = ["resolve"]

    def execute(self):
        current_platform = platform.system().lower()

        programdata = self.launch_context.env.get("PROGRAMDATA", "")
        resolve_script_api_locations = {
            "windows": (
                f"{programdata}/Blackmagic Design/"
                "DaVinci Resolve/Support/Developer/Scripting"
            ),
            "darwin": (
                "/Library/Application Support/Blackmagic Design"
                "/DaVinci Resolve/Developer/Scripting"
            ),
            "linux": "/opt/resolve/Developer/Scripting"
        }
        resolve_script_api = Path(resolve_script_api_locations[current_platform])
        self.launch_context.env["RESOLVE_SCRIPT_API"] = resolve_script_api.as_posix()

        resolve_script_lib_dirs = {
            "windows": (
                "C:/Program Files/Blackmagic Design"
                "/DaVinci Resolve/fusionscript.dll"
            ),
            "darwin": (
                "/Applications/DaVinci Resolve/DaVinci Resolve.app"
                "/Contents/Libraries/Fusion/fusionscript.so"
            ),
            "linux": "/opt/resolve/libs/Fusion/fusionscript.so"
        }
        resolve_script_lib = Path(resolve_script_lib_dirs[current_platform])
        self.launch_context.env["RESOLVE_SCRIPT_LIB"] = resolve_script_lib.as_posix()

        # TODO: add OTIO installation from `openpype/requirements.py`
        # making sure python <3.9.* is installed at provided path
        python3_home = Path(self.launch_context.env.get("RESOLVE_PYTHON3_HOME", ""))

        assert python3_home.is_dir(), (
            "Python 3 is not installed at the provided folder path. Either "
            "make sure the `environments\resolve.json` is having correctly "
            "set `RESOLVE_PYTHON3_HOME` or make sure Python 3 is installed "
            f"in given path. \nRESOLVE_PYTHON3_HOME: `{python3_home}`"
        )
        python3_home_str = python3_home.as_posix()
        self.launch_context.env["PYTHONHOME"] = python3_home_str
        self.log.info(f"Path to Resolve Python folder: `{python3_home_str}`")

        # add to the python path to PATH
        env_path = self.launch_context.env["PATH"]
        self.launch_context.env["PATH"] = f"{python3_home_str}{os.pathsep}{env_path}"

        self.log.debug(f"PATH: {self.launch_context.env['PATH']}")

        # add to the PYTHONPATH
        env_pythonpath = self.launch_context.env["PYTHONPATH"]
        modules_path = Path(resolve_script_api, "Modules").as_posix()
        self.launch_context.env["PYTHONPATH"] = f"{modules_path}{os.pathsep}{env_pythonpath}"

        self.log.debug(f"PYTHONPATH: {self.launch_context.env['PYTHONPATH']}")

        resolve_utility_scripts_dirs = {
            "windows": (
                f"{programdata}/Blackmagic Design"
                "/DaVinci Resolve/Fusion/Scripts/Comp"
            ),
            "darwin": (
                "/Library/Application Support/Blackmagic Design"
                "/DaVinci Resolve/Fusion/Scripts/Comp"
            ),
            "linux": "/opt/resolve/Fusion/Scripts/Comp"
        }
        resolve_utility_scripts_dir = Path(resolve_utility_scripts_dirs[current_platform])
        # setting utility scripts dir for scripts syncing
        self.launch_context.env["RESOLVE_UTILITY_SCRIPTS_DIR"] = resolve_utility_scripts_dir.as_posix()

        # remove terminal coloring tags
        self.launch_context.env["OPENPYPE_LOG_NO_COLORS"] = "True"

        # Resolve Setup integration
        setup(self.launch_context.env)
