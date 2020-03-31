import logging
import os

from pype.lib import PypeHook
from pypeapp import Logger

log = logging.getLogger(__name__)


class PremierePrelaunch(PypeHook):
    """
    This hook will check if current workfile path has Unreal
    project inside. IF not, it initialize it and finally it pass
    path to the project by environment variable to Unreal launcher
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
        asset = env["AVALON_ASSET"]
        task = env["AVALON_TASK"]
        workdir = env["AVALON_WORKDIR"]
        project_name = f"{asset}_{task}"

        import avalon.api
        import pype.premiere
        avalon.api.install(pype.premiere)

        try:
            __import__("pype.premiere")
            __import__("pyblish")

        except ImportError as e:
            print traceback.format_exc()
            print("pyblish: Could not load integration: %s " % e)

        else:
            # Setup integration
            import pype.premiere.lib
            pype.premiere.lib.setup()

        self.log.debug("_ self.signature: `{}`".format(self.signature))
        self.log.debug("_ asset: `{}`".format(asset))
        self.log.debug("_ task: `{}`".format(task))
        self.log.debug("_ workdir: `{}`".format(workdir))
        self.log.debug("_ project_name: `{}`".format(project_name))

        return True
