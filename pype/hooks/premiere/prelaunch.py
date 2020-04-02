import os
import traceback
from pype.lib import PypeHook
from pypeapp import Logger


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
        from pype.services.rest_api.base_class import register_statics

        if not env:
            env = os.environ

        PYPE_MODULE_ROOT = env.get("PYPE_MODULE_ROOT", None)

        asset = env["AVALON_ASSET"]
        task = env["AVALON_TASK"]
        workdir = env["AVALON_WORKDIR"]
        project_name = f"{asset}_{task}"

        import importlib
        import avalon.api
        import pype.premiere
        avalon.api.install(pype.premiere)

        try:
            __import__("pype.premiere")
            __import__("pyblish")

        except ImportError as e:
            print(traceback.format_exc())
            print("pyblish: Could not load integration: %s " % e)

        else:
            # start rest api static server
            static_site_dir_path = os.path.join(
                PYPE_MODULE_ROOT,
                "pype",
                "premiere",
                "static_ppro").replace("\\", "/")
            self.log.debug(
                "_ static_site_dir_path: `{}`".format(static_site_dir_path))
            register_statics("/ppro", static_site_dir_path)

            # Premiere Setup integration
            from pype.premiere import lib as prlib
            importlib.reload(prlib)
            prlib.setup(env)

        self.log.debug("_ self.signature: `{}`".format(self.signature))
        self.log.debug("_ asset: `{}`".format(asset))
        self.log.debug("_ task: `{}`".format(task))
        self.log.debug("_ workdir: `{}`".format(workdir))
        self.log.debug("_ project_name: `{}`".format(project_name))

        return True
