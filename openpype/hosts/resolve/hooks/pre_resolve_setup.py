import os
import importlib
from openpype.lib import PreLaunchHook
from openpype.hosts.resolve.api import utils


class ResolvePrelaunch(PreLaunchHook):
    """
    This hook will check if current workfile path has Resolve
    project inside. IF not, it initialize it and finally it pass
    path to the project by environment variable to Premiere launcher
    shell script.
    """
    app_groups = ["resolve"]

    def execute(self):
        # TODO: add OTIO installation from  `openpype/requirements.py`
        # making sure python 3.6 is installed at provided path
        py36_dir = os.path.normpath(
            self.launch_context.env.get("PYTHON36_RESOLVE", ""))
        assert os.path.isdir(py36_dir), (
            "Python 3.6 is not installed at the provided folder path. Either "
            "make sure the `environments\resolve.json` is having correctly "
            "set `PYTHON36_RESOLVE` or make sure Python 3.6 is installed "
            f"in given path. \nPYTHON36_RESOLVE: `{py36_dir}`"
        )
        self.log.info(f"Path to Resolve Python folder: `{py36_dir}`...")

        # setting utility scripts dir for scripts syncing
        us_dir = os.path.normpath(
            self.launch_context.env.get("RESOLVE_UTILITY_SCRIPTS_DIR", "")
        )
        assert os.path.isdir(us_dir), (
            "Resolve utility script dir does not exists. Either make sure "
            "the `environments\resolve.json` is having correctly set "
            "`RESOLVE_UTILITY_SCRIPTS_DIR` or reinstall DaVinci Resolve. \n"
            f"RESOLVE_UTILITY_SCRIPTS_DIR: `{us_dir}`"
        )
        self.log.debug(f"-- us_dir: `{us_dir}`")

        # correctly format path for pre python script
        pre_py_sc = os.path.normpath(
            self.launch_context.env.get("PRE_PYTHON_SCRIPT", ""))
        self.launch_context.env["PRE_PYTHON_SCRIPT"] = pre_py_sc
        self.log.debug(f"-- pre_py_sc: `{pre_py_sc}`...")
        try:
            __import__("openpype.hosts.resolve")
            __import__("pyblish")

        except ImportError:
            self.log.warning(
                "pyblish: Could not load Resolve integration.",
                exc_info=True
            )

        else:
            # Resolve Setup integration
            importlib.reload(utils)
            self.log.debug(f"-- utils.__file__: `{utils.__file__}`")
            utils.setup(self.launch_context.env)
