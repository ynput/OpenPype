import os
import importlib
from openpype.lib import PreLaunchHook, ApplicationLaunchFailed
from openpype.hosts.fusion.api import utils


class FusionPrelaunch(PreLaunchHook):
    """
    This hook will check if current workfile path has Fusion
    project inside.
    """
    app_groups = ["fusion"]

    def execute(self):
        # making sure python 3.6 is installed at provided path
        py36_dir = os.path.normpath(self.launch_context.env.get("PYTHON36", ""))
        if not os.path.isdir(py36_dir):
            raise ApplicationLaunchFailed(
                "Python 3.6 is not installed at the provided path.\n"
                "Either make sure the 'environments/fusion.json' has "
                "'PYTHON36' set corectly or make sure Python 3.6 is installed "
                f"in the given path.\n\nPYTHON36: {py36_dir}"
            )
        self.log.info(f"Path to Fusion Python folder: '{py36_dir}'...")
        self.launch_context.env["PYTHON36"] = py36_dir

        # setting utility scripts dir for scripts syncing
        us_dir = os.path.normpath(
            self.launch_context.env.get("FUSION_UTILITY_SCRIPTS_DIR", "")
        )
        if not os.path.isdir(us_dir):
            raise ApplicationLaunchFailed(
                "Fusion utility script dir does not exist. Either make sure "
                "the 'environments/fusion.json' has "
                "'FUSION_UTILITY_SCRIPTS_DIR' set correctly or reinstall "
                f"Fusion.\n\nFUSION_UTILITY_SCRIPTS_DIR: '{us_dir}'"
            )

        try:
            __import__("avalon.fusion")
            __import__("pyblish")

        except ImportError:
            self.log.warning(
                "pyblish: Could not load Fusion integration.",
                exc_info=True
            )

        else:
            # Resolve Setup integration
            importlib.reload(utils)
            utils.setup(self.launch_context.env)
