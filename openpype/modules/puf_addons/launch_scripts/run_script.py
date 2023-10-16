import os
import sys
import subprocess

from openpype.lib import (
    ApplicationManager,
    ApplicationNotFound,
    ApplictionExecutableNotFound,
    get_app_environments_for_context
)
from openpype.lib.applications import (
    ApplicationLaunchContext,
    ApplicationExecutable
)


def get_relative_executable(executable: ApplicationExecutable,
                            relative_path: str):
    """Get ApplicationExecutable relative to input ApplicationExecutable"""
    folder = os.path.dirname(str(executable))
    new_path = os.path.normpath(os.path.join(folder, relative_path))
    return ApplicationExecutable(new_path)


def run_script(
    project_name: str,
    asset_name: str,
    task_name: str,
    app_name: str,
    script_path: str,
    headless: bool=True,
    start_last_workfile: bool=False,
    env: dict=None
) -> subprocess.Popen:
    """Launch application with the given python script.

    Args:
        project_name (str): The project name.
        asset_name (str): The asset name.
        task_name (str): The task name.
        script_path (List[str]): The python script to run.

    Returns:
        Popen: The Blender process.
    """

    application_manager = ApplicationManager()
    app = application_manager.applications.get(app_name)
    if not app:
        raise ApplicationNotFound(app_name)

    executable = app.find_executable()
    if not executable:
        raise ApplictionExecutableNotFound(app)

    # Must-have for proper launch of app
    app_env = get_app_environments_for_context(
        project_name,
        asset_name,
        task_name,
        app_name
    )

    if env is None:
        env = os.environ.copy()
    env.update(app_env)

    # Application specific arguments to launch script
    host_name = app_name.split("/", 1)[0]
    app_args = []
    data = {}

    # Find the relevant host addon specific run script entry point
    # TODO: This should be moved to the relevant addons as an interface instead
    # Blender
    if host_name == "blender":
        if headless:
            app_args.append("-b")

        app_args.extend(["-P", script_path])

        # Add data to the launch context so the blender prelaunch hook
        # skips the disconnecting of the subprocess on Windows to still
        # preserve stdout/stderr
        data["batch"] = True

    # Maya
    elif host_name == "maya":
        if headless:
            if sys.platform == "win32":
                executable = get_relative_executable(executable,
                                                     "mayabatch.exe")
            else:
                app_args.append("-batch")

        # From MEL execute the Python script on launch
        # todo: maybe -script flag to point to a .mel file is easier?
        script_path = script_path.replace("\\", "/")
        python_command = (
            "import sys; "
            f"script_path = r'{script_path}'; "
            "execfile(script_path) if sys.version_info.major == 2 else "
            "exec(open(script_path).read())"
        )
        mel_command = f'python("{python_command}");'
        if not headless:
            # TODO: If the python command fails then Maya GUI mode will not
            #  close because the python command will fail. We should `catch`
            #  that instead to still force quit maya
            # If not headless, ensure to close maya afterwards
            # TODO: Is this safe for *all* scripts we want to run? What if a
            #  script itself is also using evalDeferred or alike to trigger
            #  something?
            mel_command += 'evalDeferred -lowestPriority "quit -force";'
        app_args.extend(["-command", mel_command])

    # Houdini
    elif host_name == "houdini":
        if not headless:
            raise NotImplementedError("GUI mode not supported to run script")

        executable = get_relative_executable(executable, "hython")
        app_args = [script_path]

    # Fusion
    elif host_name == "fusion":
        # Run a script on Fusion launch (Fusion 17.4+ only)
        launch_script = os.path.join(
            os.path.dirname(__file__), "scripts", "fusion_launch_script.py3"
        ).replace("\\", "/")  # escape backslashes
        script = f"fusion:RunScript(fusion:MapPath('{launch_script}'))"

        # Pass the actual script we want to trigger as env var
        env["OPENPYPE_FUSION_LAUNCH_SCRIPT_PATH"] = script_path
        app_args = ["/execute", script]

    # Nuke family
    elif host_name in {"nuke", "nukex", "nukestudio"}:
        # -t is always in no gui mode.
        # note: -tg could be used to create QApplication instance
        app_args = ["-t", script_path]

    else:
        raise NotImplementedError(f"Host not supported: {host_name}")

    data.update(dict(
        app_args=app_args,
        project_name=project_name,
        asset_name=asset_name,
        task_name=task_name,
        env=env,
        start_last_workfile=start_last_workfile,
    ))
    context = ApplicationLaunchContext(
        app, executable, **data
    )

    # TODO: Do not hardcode this - we might not always want to capture output
    #  and especially not stderr -> stdout. For now this is used to capture
    #  the output from the subprocess and log the output accordingly
    context.kwargs["stdout"] = subprocess.PIPE
    context.kwargs["stderr"] = subprocess.STDOUT

    return context.launch()
