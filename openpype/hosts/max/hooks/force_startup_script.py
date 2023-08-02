# -*- coding: utf-8 -*-
"""Pre-launch to force 3ds max startup script."""
import os
from openpype.lib import PreLaunchHook
from openpype.hosts.max import MAX_HOST_DIR


class ForceStartupScript(PreLaunchHook):
    """Inject OpenPype environment to 3ds max.

    Note that this works in combination whit 3dsmax startup script that
    is translating it back to PYTHONPATH for cases when 3dsmax drops PYTHONPATH
    environment.

    Hook `GlobalHostDataHook` must be executed before this hook.
    """
    app_groups = ["3dsmax"]
    order = 11

    def execute(self):
        startup_args = [
            "-U",
            "MAXScript",
            os.path.join(MAX_HOST_DIR, "startup", "startup.ms"),
        ]
        self.launch_context.launch_args.append(startup_args)
