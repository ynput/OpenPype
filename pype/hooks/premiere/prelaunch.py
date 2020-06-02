import os
import traceback
from pype.lib import PypeHook
from pype.api import Logger
from pype.hosts.premiere import lib as prlib


class PremierePrelaunch(PypeHook):
    """
    This hook will check if current workfile path has Adobe Premiere
    project inside. IF not, it initialize it and finally it pass
    path to the project by environment variable to Premiere launcher
    shell script.
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

        try:
            __import__("pype.hosts.premiere")
            __import__("pyblish")

        except ImportError as e:
            print(traceback.format_exc())
            print("pyblish: Could not load integration: %s " % e)

        else:
            # Premiere Setup integration
            # importlib.reload(prlib)
            prlib.setup(env)

        return True
