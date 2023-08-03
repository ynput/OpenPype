# -*- coding: utf-8 -*-
"""Pre-launch hook to inject python environment."""
import os
from openpype.lib.applications import PreLaunchHook, LaunchTypes


class InjectPythonPath(PreLaunchHook):
    """Inject OpenPype environment to 3dsmax.

    Note that this works in combination whit 3dsmax startup script that
    is translating it back to PYTHONPATH for cases when 3dsmax drops PYTHONPATH
    environment.

    Hook `GlobalHostDataHook` must be executed before this hook.
    """
    app_groups = {"3dsmax"}
    launch_types = {LaunchTypes.local}

    def execute(self):
        self.launch_context.env["MAX_PYTHONPATH"] = os.environ["PYTHONPATH"]
