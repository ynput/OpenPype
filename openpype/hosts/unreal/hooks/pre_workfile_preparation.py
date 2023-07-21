# -*- coding: utf-8 -*-
"""Hook to launch Unreal and prepare projects."""
import os
import copy
from pathlib import Path
from openpype.widgets.splash_screen import SplashScreen
from qtpy import QtCore
from openpype.hosts.unreal.ue_workers import (
    UEProjectGenerationWorker,
    UEPluginInstallWorker
)

from openpype import resources
from openpype.lib import (
    PreLaunchHook,
    ApplicationLaunchFailed,
    ApplicationNotFound,
    get_workfile_template_key,
    get_openpype_execute_args
)
from openpype.pipeline.workfile import get_workfile_template_key
import openpype.hosts.unreal.lib as unreal_lib


class UnrealPrelaunchHook(PreLaunchHook):
    """Hook to handle launching Unreal.

    This hook will check if current workfile path has Unreal
    project inside. IF not, it initializes it, and finally it pass
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
        anatomy = self.data["anatomy"]
        project_doc = self.data["project_doc"]

        # Use already prepared workdir data
        workdir_data = copy.deepcopy(self.data["workdir_data"])
        task_type = workdir_data.get("task", {}).get("type")

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
        template_obj = anatomy.templates_obj[workfile_template_key]["file"]

        # Return filename
        return template_obj.format_strict(workdir_data)

    def exec_plugin_install(self, engine_path: Path, env: dict = None):
        # set up the QThread and worker with necessary signals
        env = env or os.environ
        q_thread = QtCore.QThread()
        ue_plugin_worker = UEPluginInstallWorker()

        q_thread.started.connect(ue_plugin_worker.run)
        ue_plugin_worker.setup(engine_path, env)
        ue_plugin_worker.moveToThread(q_thread)

        splash_screen = SplashScreen(
            "Installing plugin",
            resources.get_resource("app_icons", "ue4.png")
        )

        # set up the splash screen with necessary triggers
        ue_plugin_worker.installing.connect(
            splash_screen.update_top_label_text
        )
        ue_plugin_worker.progress.connect(splash_screen.update_progress)
        ue_plugin_worker.log.connect(splash_screen.append_log)
        ue_plugin_worker.finished.connect(splash_screen.quit_and_close)
        ue_plugin_worker.failed.connect(splash_screen.fail)

        splash_screen.start_thread(q_thread)
        splash_screen.show_ui()

        if not splash_screen.was_proc_successful():
            raise ApplicationLaunchFailed("Couldn't run the application! "
                                          "Plugin failed to install!")

    def exec_ue_project_gen(self,
                            engine_version: str,
                            unreal_project_name: str,
                            engine_path: Path,
                            project_dir: Path):
        self.log.info((
            f"{self.signature} Creating unreal "
            f"project [ {unreal_project_name} ]"
        ))

        q_thread = QtCore.QThread()
        ue_project_worker = UEProjectGenerationWorker()
        ue_project_worker.setup(
            engine_version,
            self.data["project_name"],
            unreal_project_name,
            engine_path,
            project_dir
        )
        ue_project_worker.moveToThread(q_thread)
        q_thread.started.connect(ue_project_worker.run)

        splash_screen = SplashScreen(
            "Initializing UE project",
            resources.get_resource("app_icons", "ue4.png")
        )

        ue_project_worker.stage_begin.connect(
            splash_screen.update_top_label_text
        )
        ue_project_worker.progress.connect(splash_screen.update_progress)
        ue_project_worker.log.connect(splash_screen.append_log)
        ue_project_worker.finished.connect(splash_screen.quit_and_close)
        ue_project_worker.failed.connect(splash_screen.fail)

        splash_screen.start_thread(q_thread)
        splash_screen.show_ui()

        if not splash_screen.was_proc_successful():
            raise ApplicationLaunchFailed("Couldn't run the application! "
                                          "Failed to generate the project!")

    def execute(self):
        """Hook entry method."""
        workdir = self.launch_context.env["AVALON_WORKDIR"]
        executable = str(self.launch_context.executable)
        engine_version = self.app_name.split("/")[-1].replace("-", ".")
        try:
            if int(engine_version.split(".")[0]) < 4 and \
                    int(engine_version.split(".")[1]) < 26:
                raise ApplicationLaunchFailed((
                    f"{self.signature} Old unsupported version of UE "
                    f"detected - {engine_version}"))
        except ValueError:
            # there can be string in minor version and in that case
            # int cast is failing. This probably happens only with
            # early access versions and is of no concert for this check
            # so let's keep it quiet.
            ...

        unreal_project_filename = self._get_work_filename()
        unreal_project_name = os.path.splitext(unreal_project_filename)[0]
        # Unreal is sensitive about project names longer then 20 chars
        if len(unreal_project_name) > 20:
            raise ApplicationLaunchFailed(
                f"Project name exceeds 20 characters ({unreal_project_name})!"
            )

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
            f"{self.signature} requested UE version: "
            f"[ {engine_version} ]"
        ))

        project_path.mkdir(parents=True, exist_ok=True)

        # Set "AYON_UNREAL_PLUGIN" to current process environment for
        # execution of `create_unreal_project`

        if self.launch_context.env.get("AYON_UNREAL_PLUGIN"):
            self.log.info((
                f"{self.signature} using Ayon plugin from "
                f"{self.launch_context.env.get('AYON_UNREAL_PLUGIN')}"
            ))
        env_key = "AYON_UNREAL_PLUGIN"
        if self.launch_context.env.get(env_key):
            os.environ[env_key] = self.launch_context.env[env_key]

        # engine_path points to the specific Unreal Engine root
        # so, we are going up from the executable itself 3 levels.
        engine_path: Path = Path(executable).parents[3]

        if not unreal_lib.check_plugin_existence(engine_path):
            self.exec_plugin_install(engine_path)

        project_file = project_path / unreal_project_filename

        if not project_file.is_file():
            self.exec_ue_project_gen(engine_version,
                                     unreal_project_name,
                                     engine_path,
                                     project_path)

        self.launch_context.env["AYON_UNREAL_VERSION"] = engine_version

        new_launch_args = get_openpype_execute_args(
            "run", self.launch_script_path(), executable,
        )

        # Append as whole list as these areguments should not be separated
        self.launch_context.launch_args = new_launch_args

        # Append project file to launch arguments
        self.launch_context.launch_args.append(
            f"\"{project_file.as_posix()}\"")

    def launch_script_path(self):
        from openpype.hosts.unreal import get_launch_script_path

        return get_launch_script_path()
