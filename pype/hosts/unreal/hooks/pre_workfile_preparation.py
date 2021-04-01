import os

from openpype.lib import (
    PreLaunchHook,
    ApplicationLaunchFailed
)
from openpype.hosts.unreal.api import lib as unreal_lib


class UnrealPrelaunchHook(PreLaunchHook):
    """
    This hook will check if current workfile path has Unreal
    project inside. IF not, it initialize it and finally it pass
    path to the project by environment variable to Unreal launcher
    shell script.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.signature = "( {} )".format(self.__class__.__name__)

    def execute(self):
        asset_name = self.data["asset_name"]
        task_name = self.data["task_name"]
        workdir = self.env["AVALON_WORKDIR"]
        engine_version = self.app_name.split("_")[-1]
        unreal_project_name = f"{asset_name}_{task_name}"

        # Unreal is sensitive about project names longer then 20 chars
        if len(unreal_project_name) > 20:
            self.log.warning((
                f"Project name exceed 20 characters ({unreal_project_name})!"
            ))

        # Unreal doesn't accept non alphabet characters at the start
        # of the project name. This is because project name is then used
        # in various places inside c++ code and there variable names cannot
        # start with non-alpha. We append 'P' before project name to solve it.
        # 😱
        if not unreal_project_name[:1].isalpha():
            self.log.warning((
                "Project name doesn't start with alphabet "
                f"character ({unreal_project_name}). Appending 'P'"
            ))
            unreal_project_name = f"P{unreal_project_name}"

        project_path = os.path.join(workdir, unreal_project_name)

        self.log.info((
            f"{self.signature} requested UE4 version: "
            f"[ {engine_version} ]"
        ))

        detected = unreal_lib.get_engine_versions()
        detected_str = ', '.join(detected.keys()) or 'none'
        self.log.info((
            f"{self.signature} detected UE4 versions: "
            f"[ {detected_str} ]"
        ))

        engine_version = ".".join(engine_version.split(".")[:2])
        if engine_version not in detected.keys():
            raise ApplicationLaunchFailed((
                f"{self.signature} requested version not "
                f"detected [ {engine_version} ]"
            ))

        os.makedirs(project_path, exist_ok=True)

        project_file = os.path.join(
            project_path,
            f"{unreal_project_name}.uproject"
        )
        if not os.path.isfile(project_file):
            engine_path = detected[engine_version]
            self.log.info((
                f"{self.signature} creating unreal "
                f"project [ {unreal_project_name} ]"
            ))
            # Set "AVALON_UNREAL_PLUGIN" to current process environment for
            # execution of `create_unreal_project`
            env_key = "AVALON_UNREAL_PLUGIN"
            if self.env.get(env_key):
                os.environ[env_key] = self.env[env_key]

            unreal_lib.create_unreal_project(
                unreal_project_name,
                engine_version,
                project_path,
                engine_path=engine_path
            )

        # Append project file to launch arguments
        self.launch_context.launch_args.append(f"\"{project_file}\"")
