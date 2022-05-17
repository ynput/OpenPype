# -*- coding: utf-8 -*-
"""Hook to launch Unreal and prepare projects."""
import os
from pathlib import Path

from openpype.lib import (
    PreLaunchHook,
    ApplicationLaunchFailed,
    ApplicationNotFound,
    get_workdir_data,
    get_workfile_template_key
)
import openpype.hosts.unreal.lib as unreal_lib


class UnrealPrelaunchHook(PreLaunchHook):
    """Hook to handle launching Unreal.

    This hook will check if current workfile path has Unreal
    project inside. IF not, it initialize it and finally it pass
    path to the project by environment variable to Unreal launcher
    shell script.

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.signature = f"( {self.__class__.__name__} )"

    def _get_work_filename(self):
        # Use last workfile if was found
        if self.data.get("last_workfile_path"):
            last_workfile = Path(self.data.get("last_workfile_path"))
            if last_workfile and last_workfile.exists():
                return last_workfile.name

        # Prepare data for fill data and for getting workfile template key
        task_name = self.data["task_name"]
        anatomy = self.data["anatomy"]
        asset_doc = self.data["asset_doc"]
        project_doc = self.data["project_doc"]

        asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
        task_info = asset_tasks.get(task_name) or {}
        task_type = task_info.get("type")

        workdir_data = get_workdir_data(
            project_doc, asset_doc, task_name, self.host_name
        )
        # QUESTION raise exception if version is part of filename template?
        workdir_data["version"] = 1
        workdir_data["ext"] = "uproject"

        # Get workfile template key for current context
        workfile_template_key = get_workfile_template_key(
            task_type,
            self.host_name,
            project_name=project_doc["name"]
        )
        # Fill templates
        filled_anatomy = anatomy.format(workdir_data)

        # Return filename
        return filled_anatomy[workfile_template_key]["file"]

    def execute(self):
        """Hook entry method."""
        workdir = self.launch_context.env["AVALON_WORKDIR"]
        engine_version = self.app_name.split("/")[-1].replace("-", ".")
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

        unreal_project_filename = self._get_work_filename()
        unreal_project_name = os.path.splitext(unreal_project_filename)[0]
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
            unreal_project_filename = f'{unreal_project_name}.uproject'

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

        self.launch_context.launch_args = [ue4_path.as_posix()]
        project_path.mkdir(parents=True, exist_ok=True)

        project_file = project_path / unreal_project_filename
        if not project_file.is_file():
            engine_path = detected[engine_version]
            self.log.info((
                f"{self.signature} creating unreal "
                f"project [ {unreal_project_name} ]"
            ))
            # Set "OPENPYPE_UNREAL_PLUGIN" to current process environment for
            # execution of `create_unreal_project`
            if self.launch_context.env.get("OPENPYPE_UNREAL_PLUGIN"):
                self.log.info((
                    f"{self.signature} using OpenPype plugin from "
                    f"{self.launch_context.env.get('OPENPYPE_UNREAL_PLUGIN')}"
                ))
            env_key = "OPENPYPE_UNREAL_PLUGIN"
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
