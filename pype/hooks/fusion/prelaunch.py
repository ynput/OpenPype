import os
import traceback
import importlib
from pype.lib import PypeHook
from pypeapp import Logger
from pype.hosts.fusion import utils


class FusionPrelaunch(PypeHook):
    """
    This hook will check if current workfile path has Fusion
    project inside.
    """

    def __init__(self, logger=None):
        if not logger:
            self.log = Logger().get_logger(self.__class__.__name__)
        else:
            self.log = logger

        self.signature = "( {} )".format(self.__class__.__name__)

    def execute(self, *args, env: dict = None) -> bool:

        if not env:
            env = os.environ

        # making sure pyton 3.6 is installed at provided path
        py36_dir = os.path.normpath(env.get("PYTHON36", ""))
        assert os.path.isdir(py36_dir), (
            "Python 3.6 is not installed at the provided folder path. Either "
            "make sure the `environments\resolve.json` is having correctly "
            "set `PYTHON36` or make sure Python 3.6 is installed "
            f"in given path. \nPYTHON36E: `{py36_dir}`"
        )
        self.log.info(f"Path to Fusion Python folder: `{py36_dir}`...")
        env["PYTHON36"] = py36_dir

        # setting utility scripts dir for scripts syncing
        us_dir = os.path.normpath(env.get("FUSION_UTILITY_SCRIPTS_DIR", ""))
        assert os.path.isdir(us_dir), (
            "Fusion utility script dir does not exists. Either make sure "
            "the `environments\fusion.json` is having correctly set "
            "`FUSION_UTILITY_SCRIPTS_DIR` or reinstall DaVinci Resolve. \n"
            f"FUSION_UTILITY_SCRIPTS_DIR: `{us_dir}`"
        )

        try:
            __import__("avalon.fusion")
            __import__("pyblish")

        except ImportError as e:
            print(traceback.format_exc())
            print("pyblish: Could not load integration: %s " % e)

        else:
            # Resolve Setup integration
            importlib.reload(utils)
            utils.setup(env)

        return True
