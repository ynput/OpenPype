# -*- coding: utf-8 -*-
"""Pre-launch hook to inject python environment."""
from openpype.lib import PreLaunchHook
import os


class InjectPythonPath(PreLaunchHook):
    """Inject OpenPype environment to 3dsmax.

    Note that this works in combination whit 3dsmax startup script that
    is translating it back to PYTHONPATH for cases when 3dsmax drops PYTHONPATH
    environment.

    Hook `GlobalHostDataHook` must be executed before this hook.
    """
    app_groups = ["3dsmax"]

    def execute(self):
        self.launch_context.env["MAX_PYTHONPATH"] = os.environ["PYTHONPATH"]
