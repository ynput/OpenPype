import os
from openpype.lib import PreLaunchHook
from openpype_modules.slack import SLACK_MODULE_DIR


class PrePython2Support(PreLaunchHook):
    """Add python slack api module for Python 2 to PYTHONPATH.

    Path to vendor modules is added to the beginning of PYTHONPATH.
    """

    def execute(self):
        if not self.application.use_python_2:
            return

        self.log.info("Adding Slack Python 2 packages to PYTHONPATH.")

        # Prepare vendor dir path
        python_2_vendor = os.path.join(SLACK_MODULE_DIR, "python2_vendor")

        # Add Python 2 modules
        python_paths = [
            # `python-ftrack-api`
            os.path.join(python_2_vendor, "python-slack-sdk-1", "slackclient"),
            os.path.join(python_2_vendor, "python-slack-sdk-1")
        ]
        self.log.info("python_paths {}".format(python_paths))
        # Load PYTHONPATH from current launch context
        python_path = self.launch_context.env.get("PYTHONPATH")
        if python_path:
            python_paths.append(python_path)

        # Set new PYTHONPATH to launch context environments
        self.launch_context.env["PYTHONPATH"] = os.pathsep.join(python_paths)
