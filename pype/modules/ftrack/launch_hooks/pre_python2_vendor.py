import os
from pype.lib import PreLaunchHook
from pype.modules.ftrack import FTRACK_MODULE_DIR


class PrePyhton2Support(PreLaunchHook):
    """Add python ftrack api module for Python 2 to PYTHONPATH.

    Path to vendor modules is added to the beggining of PYTHONPATH.
    """
    # There will be needed more granular filtering in future
    app_groups = ["maya", "nuke", "nukex", "hiero", "nukestudio"]

    def execute(self):
        # Prepare dir path
        python2_vendor = os.path.join(FTRACK_MODULE_DIR, "python2_vendor")
        # Load PYTHONPATH from current launch context
        python_path = self.launch_context.env.get("PYTHONPATH")

        # Just override if PYTHONPATH is not set yet
        if not python_path:
            python_path = python2_vendor
        else:
            python_path = os.pathsep.join([python2_vendor, python_path])

        # Set new PYTHONPATH to launch context environments
        self.launch_context.env["PYTHONPATH"] = python_path
