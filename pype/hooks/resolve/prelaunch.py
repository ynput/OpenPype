import os
import traceback
from pype.lib import PypeHook
from pypeapp import Logger
from pype.resolve import lib as rlib


class ResolvePrelaunch(PypeHook):
    """
    This hook will check if current workfile path has Resolve
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
            __import__("pype.resolve")
            __import__("pyblish")

        except ImportError as e:
            print(traceback.format_exc())
            print("pyblish: Could not load integration: %s " % e)

        else:
            # Resolve Setup integration
            # importlib.reload(prlib)
            rlib.setup(env)

        return True
