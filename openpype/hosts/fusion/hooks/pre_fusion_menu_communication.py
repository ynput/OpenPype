import subprocess
import os
from openpype.lib.applications import (
    PreLaunchHook,
    LaunchTypes,
)
from openpype.lib import get_openpype_execute_args
from openpype.lib.execute import run_detached_process


class FusionMenuCommunication(PreLaunchHook):
    """
    Prepares OpenPype Fusion socket communication.
    Takes the path of the fusion executable and
    sets up a socket for the menu communication.
    """

    app_groups = {"fusion"}
    order = 3
    launch_types = {LaunchTypes.local}
    name = "fusion"

    def execute(self):
        self.log.info("Starting socket listener")

        # Get the current script's directory
        current_script_dir = os.path.dirname(os.path.abspath(__file__))

        # Define the path to the script you want to run
        script_to_run = os.path.join(
            current_script_dir, "..", "api", "menu_communication.py"
        )

        # Use subprocess to start the new process
        # subprocess_args = get_openpype_execute_args("run", script_to_run)
        # run_detached_process(subprocess_args)

        args = get_openpype_execute_args(
            "module", "fusionmenulistener", "launch"
        )
        run_detached_process(args, env=self.launch_context.env)
