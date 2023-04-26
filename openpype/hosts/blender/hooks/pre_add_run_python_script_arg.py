from pathlib import Path

from openpype.lib import PreLaunchHook
from openpype.settings.lib import get_project_settings


class AddPythonScriptToLaunchArgs(PreLaunchHook):
    """Add python script to be executed before Blender launch."""

    # Append after file argument
    order = 15
    app_groups = [
        "blender",
    ]

    def execute(self):
        # Check enabled in settings
        project_name = self.data["project_name"]
        project_settings = get_project_settings(project_name)
        host_name = self.application.host_name
        host_settings = project_settings.get(host_name)
        if not host_settings:
            self.log.info(f"""Host "{host_name}" doesn\'t have settings""")
            return None

        # Add path to workfile to arguments
        for python_script_path in self.launch_context.data.get(
            "python_scripts", []
        ):
            self.log.info(
                f"Adding python script {python_script_path} to launch"
            )
            # Test script path exists
            if not Path(python_script_path).exists():
                raise ValueError(
                    f"Python script {python_script_path} doesn't exist."
                )

            if "--" in self.launch_context.launch_args:
                # Insert before separator
                separator_index = self.launch_context.launch_args.index("--")
                self.launch_context.launch_args.insert(
                    separator_index,
                    "-P",
                )
                self.launch_context.launch_args.insert(
                    separator_index + 1,
                    Path(python_script_path).as_posix(),
                )
            else:
                self.launch_context.launch_args.extend(
                    ["-P", Path(python_script_path).as_posix()]
                )

        # Ensure separator
        if "--" not in self.launch_context.launch_args:
            self.launch_context.launch_args.append("--")

        self.launch_context.launch_args.extend(
            [*self.launch_context.data.get("script_args", [])]
        )
