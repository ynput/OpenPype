import logging
import os

from pype.lib import PypeHook
from pype.hosts.unreal import lib as unreal_lib
from pype.api import Logger

log = logging.getLogger(__name__)


class UnrealPrelaunch(PypeHook):
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
        engine_version = env["AVALON_APP_NAME"].split("_")[-1]
        project_name = f"{asset}_{task}"

        # Unreal is sensitive about project names longer then 20 chars
        if len(project_name) > 20:
            self.log.warning((f"Project name exceed 20 characters "
                              f"({project_name})!"))

        # Unreal doesn't accept non alphabet characters at the start
        # of the project name. This is because project name is then used
        # in various places inside c++ code and there variable names cannot
        # start with non-alpha. We append 'P' before project name to solve it.
        # 😱
        if not project_name[:1].isalpha():
            self.log.warning(f"Project name doesn't start with alphabet "
                             f"character ({project_name}). Appending 'P'")
            project_name = f"P{project_name}"

        project_path = os.path.join(workdir, project_name)

        self.log.info((f"{self.signature} requested UE4 version: "
                       f"[ {engine_version} ]"))

        detected = unreal_lib.get_engine_versions()
        detected_str = ', '.join(detected.keys()) or 'none'
        self.log.info((f"{self.signature} detected UE4 versions: "
                       f"[ {detected_str} ]"))
        del(detected_str)
        engine_version = ".".join(engine_version.split(".")[:2])
        if engine_version not in detected.keys():
            self.log.error((f"{self.signature} requested version not "
                            f"detected [ {engine_version} ]"))
            return False

        os.makedirs(project_path, exist_ok=True)

        project_file = os.path.join(project_path, f"{project_name}.uproject")
        engine_path = detected[engine_version]
        if not os.path.isfile(project_file):
            self.log.info((f"{self.signature} creating unreal "
                           f"project [ {project_name} ]"))
            if env.get("AVALON_UNREAL_PLUGIN"):
                os.environ["AVALON_UNREAL_PLUGIN"] = env.get("AVALON_UNREAL_PLUGIN")  # noqa: E501
            unreal_lib.create_unreal_project(project_name,
                                             engine_version,
                                             project_path,
                                             engine_path=engine_path)

        env["PYPE_UNREAL_PROJECT_FILE"] = project_file
        env["AVALON_CURRENT_UNREAL_ENGINE"] = engine_path
        return True
