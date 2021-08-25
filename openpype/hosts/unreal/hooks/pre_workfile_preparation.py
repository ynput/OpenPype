# -*- coding: utf-8 -*-
"""Hook to launch Unreal and prepare projects."""
import os
from pathlib import Path

from openpype.lib import (
    PreLaunchHook,
    ApplicationLaunchFailed,
    ApplicationNotFound
)
from openpype.hosts.unreal.api import lib as unreal_lib


class UnrealPrelaunchHook(PreLaunchHook):
    """Hook to handle launching Unreal.

    This hook will check if current workfile path has Unreal
    project inside. IF not, it initialize it and finally it pass
    path to the project by environment variable to Unreal launcher
    shell script.

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.signature = "( {} )".format(self.__class__.__name__)

    def execute(self):
        """Hook entry method."""
        asset_name = self.data["asset_name"]
        task_name = self.data["task_name"]
        workdir = self.launch_context.env["AVALON_WORKDIR"]
        engine_version = self.app_name.split("/")[-1].replace("-", ".")
        unreal_project_name = f"{asset_name}_{task_name}"
        try:
            if int(engine_version.split(".")[0]) < 4 and \
                    int(engine_version.split(".")[1]) < 26:
                raise ApplicationLaunchFailed((
                    f"{self.signature} Old unsupported version of UE4 "
                    f"detected - {engine_version}"))
        except ValueError:
            # there can be string in minor version and in that case
            # int cast is failing. This probably happens only with
            # early access versions and is of no concert for this check
            # so lets keep it quite.
            ...

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

        project_path = Path(os.path.join(workdir, unreal_project_name))

        self.log.info((
            f"{self.signature} requested UE4 version: "
            f"[ {engine_version} ]"
        ))

        detected = unreal_lib.get_engine_versions(self.launch_context.env)
        detected_str = ', '.join(detected.keys()) or 'none'
        self.log.info((
            f"{self.signature} detected UE4 versions: "
            f"[ {detected_str} ]"
        ))
        if not detected:
            raise ApplicationNotFound("No Unreal Engines are found.")

        engine_version = ".".join(engine_version.split(".")[:2])
        if engine_version not in detected.keys():
            raise ApplicationLaunchFailed((
                f"{self.signature} requested version not "
                f"detected [ {engine_version} ]"
            ))

        ue4_path = unreal_lib.get_editor_executable_path(
            Path(detected[engine_version]))

        self.launch_context.launch_args.append(ue4_path.as_posix())
        project_path.mkdir(parents=True, exist_ok=True)

        project_file = project_path / f"{unreal_project_name}.uproject"
        if not project_file.is_file():
            engine_path = detected[engine_version]
            self.log.info((
                f"{self.signature} creating unreal "
                f"project [ {unreal_project_name} ]"
            ))
            # Set "AVALON_UNREAL_PLUGIN" to current process environment for
            # execution of `create_unreal_project`
            env_key = "AVALON_UNREAL_PLUGIN"
            if self.launch_context.env.get(env_key):
                os.environ[env_key] = self.launch_context.env[env_key]

            unreal_lib.create_unreal_project(
                unreal_project_name,
                engine_version,
                project_path,
                engine_path=Path(engine_path)
            )

        # Append project file to launch arguments
        self.launch_context.launch_args.append(
            f"\"{project_file.as_posix()}\"")
