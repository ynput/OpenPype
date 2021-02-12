import os

import avalon
from pype.lib import (
    PreLaunchHook,
    get_pype_execute_args
)


class PhotoshopPrelaunchHook(PreLaunchHook):
    """Launch arguments preparation.

    Hook add python executable and execute python script of photoshop
    implementation before photoshop executable.
    """
    app_groups = ["photoshop"]

    def execute(self):
        # Pop executable
        executable_path = self.launch_context.launch_args.pop(0)

        # Pop rest of launch arguments - There should not be other arguments!
        remainders = []
        while self.launch_context.launch_args:
            remainders.append(self.launch_context.launch_args.pop(0))

        script_path = self.get_launch_script_path()
        new_launch_args = get_pype_execute_args(
            "run", script_path, executable_path
        )
        # Add workfile path if exists
        workfile_path = self.data["last_workfile_path"]
        if os.path.exists(workfile_path):
            new_launch_args.append(workfile_path)

        # Append as whole list as these areguments should not be separated
        self.launch_context.launch_args.append(new_launch_args)

        if remainders:
            self.log.warning((
                "There are unexpected launch arguments in Photoshop launch. {}"
            ).format(str(remainders)))
            self.launch_context.launch_args.extend(remainders)

    def get_launch_script_path(self):
        """Path to launch script of photoshop implementation."""
        avalon_dir = os.path.dirname(os.path.abspath(avalon.__file__))
        script_path = os.path.join(
            avalon_dir,
            "photoshop",
            "launch_script.py"
        )
        return script_path
