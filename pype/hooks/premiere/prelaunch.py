import os
import traceback
from pype.lib import PypeHook
from pypeapp import Logger
import importlib
import avalon.api
import pype.premiere
from pype.premiere import lib as prlib


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

        asset = env["AVALON_ASSET"]
        task = env["AVALON_TASK"]
        workdir = env["AVALON_WORKDIR"]
        project_name = f"{asset}_{task}"
        project_path = os.path.join(workdir, project_name)
        os.makedirs(project_path, exist_ok=True)

        project_file = os.path.join(project_path, f"{project_name}.pproj")
        env["PYPE_ADOBE_PREMIERE_PROJECT_FILE"] = project_file

        # TODO: try to set workfile for premiere if it is possible
        # set workdir to the current path for premiere to open in it
        self.log.debug("_ project_path: `{}`".format(project_path))
        self.log.debug("_ project_file: `{}`".format(project_file))

        # install premiere to avalon
        avalon.api.install(pype.premiere)

        try:
            __import__("pype.premiere")
            __import__("pyblish")

        except ImportError as e:
            print(traceback.format_exc())
            print("pyblish: Could not load integration: %s " % e)

        else:
            # Premiere Setup integration
            importlib.reload(prlib)
            prlib.setup(env)

        return True
