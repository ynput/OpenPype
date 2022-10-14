import os
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

        PROGRAMDATA = self.launch_context.env["PROGRAMDATA"]
        RESOLVE_SCRIPT_API_ = {
            "windows": (
                f"{PROGRAMDATA}/Blackmagic Design/"
                "DaVinci Resolve/Support/Developer/Scripting"
            ),
            "darwin": (
                "/Library/Application Support/Blackmagic Design"
                "/DaVinci Resolve/Developer/Scripting"
            ),
            "linux": "/opt/resolve/Developer/Scripting"
        }
        RESOLVE_SCRIPT_API = os.path.normpath(
            RESOLVE_SCRIPT_API_[current_platform])
        self.launch_context.env["RESOLVE_SCRIPT_API"] = RESOLVE_SCRIPT_API

        RESOLVE_SCRIPT_LIB_ = {
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
        RESOLVE_SCRIPT_LIB = os.path.normpath(
            RESOLVE_SCRIPT_LIB_[current_platform])
        self.launch_context.env["RESOLVE_SCRIPT_LIB"] = RESOLVE_SCRIPT_LIB

        # TODO: add OTIO installation from  `openpype/requirements.py`
        # making sure python <3.9.* is installed at provided path
        python3_home = os.path.normpath(
            self.launch_context.env.get("RESOLVE_PYTHON3_HOME", ""))

        assert os.path.isdir(python3_home), (
            "Python 3 is not installed at the provided folder path. Either "
            "make sure the `environments\resolve.json` is having correctly "
            "set `RESOLVE_PYTHON3_HOME` or make sure Python 3 is installed "
            f"in given path. \nRESOLVE_PYTHON3_HOME: `{python3_home}`"
        )
        self.launch_context.env["PYTHONHOME"] = python3_home
        self.log.info(f"Path to Resolve Python folder: `{python3_home}`...")

        # add to the python path to path
        env_path = self.launch_context.env["PATH"]
        self.launch_context.env["PATH"] = os.pathsep.join([
            python3_home,
            os.path.join(python3_home, "Scripts")
        ] + env_path.split(os.pathsep))

        self.log.debug(f"PATH: {self.launch_context.env['PATH']}")

        # add to the PYTHONPATH
        env_pythonpath = self.launch_context.env["PYTHONPATH"]
        self.launch_context.env["PYTHONPATH"] = os.pathsep.join([
            os.path.join(python3_home, "Lib", "site-packages"),
            os.path.join(RESOLVE_SCRIPT_API, "Modules"),
        ] + env_pythonpath.split(os.pathsep))

        self.log.debug(f"PYTHONPATH: {self.launch_context.env['PYTHONPATH']}")

        RESOLVE_UTILITY_SCRIPTS_DIR_ = {
            "windows": (
                f"{PROGRAMDATA}/Blackmagic Design"
                "/DaVinci Resolve/Fusion/Scripts/Comp"
            ),
            "darwin": (
                "/Library/Application Support/Blackmagic Design"
                "/DaVinci Resolve/Fusion/Scripts/Comp"
            ),
            "linux": "/opt/resolve/Fusion/Scripts/Comp"
        }
        RESOLVE_UTILITY_SCRIPTS_DIR = os.path.normpath(
            RESOLVE_UTILITY_SCRIPTS_DIR_[current_platform]
        )
        # setting utility scripts dir for scripts syncing
        self.launch_context.env["RESOLVE_UTILITY_SCRIPTS_DIR"] = (
            RESOLVE_UTILITY_SCRIPTS_DIR)

        # remove terminal coloring tags
        self.launch_context.env["OPENPYPE_LOG_NO_COLORS"] = "True"

        # Resolve Setup integration
        setup(self.launch_context.env)
