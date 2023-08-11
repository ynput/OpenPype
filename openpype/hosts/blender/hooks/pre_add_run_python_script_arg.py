from pathlib import Path

from openpype.lib.applications import PreLaunchHook, LaunchTypes


class AddPythonScriptToLaunchArgs(PreLaunchHook):
    """Add python script to be executed before Blender launch."""

    # Append after file argument
    order = 15
    app_groups = {"blender"}
    launch_types = {LaunchTypes.local}

    def execute(self):
        if not self.launch_context.data.get("python_scripts"):
            return

        # Add path to workfile to arguments
        for python_script_path in self.launch_context.data["python_scripts"]:
            self.log.info(
                f"Adding python script {python_script_path} to launch"
            )
            # Test script path exists
            python_script_path = Path(python_script_path)
            if not python_script_path.exists():
                self.log.warning(
                    f"Python script {python_script_path} doesn't exist. "
                    "Skipped..."
                )
                continue

            if "--" in self.launch_context.launch_args:
                # Insert before separator
                separator_index = self.launch_context.launch_args.index("--")
                self.launch_context.launch_args.insert(
                    separator_index,
                    "-P",
                )
                self.launch_context.launch_args.insert(
                    separator_index + 1,
                    python_script_path.as_posix(),
                )
            else:
                self.launch_context.launch_args.extend(
                    ["-P", python_script_path.as_posix()]
                )

        # Ensure separator
        if "--" not in self.launch_context.launch_args:
            self.launch_context.launch_args.append("--")

        self.launch_context.launch_args.extend(
            [*self.launch_context.data.get("script_args", [])]
        )
