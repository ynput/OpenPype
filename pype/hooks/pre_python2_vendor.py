import os
from pype.lib import PreLaunchHook


class PrePython2Vendor(PreLaunchHook):
    """Prepend python 2 dependencies for py2 hosts."""
    # WARNING This hook will probably be deprecated in Pype 3 - kept for test
    order = 10
    app_groups = ["hiero", "nuke", "nukex"]

    def execute(self):
        # Prepare vendor dir path
        self.log.info("adding global python 2 vendor")
        pype_root = os.getenv("OPENPYPE_ROOT")
        python_2_vendor = os.path.join(
            pype_root,
            "pype",
            "vendor",
            "python",
            "python_2"
        )

        # Add Python 2 modules
        python_paths = [
            python_2_vendor
        ]

        # Load PYTHONPATH from current launch context
        python_path = self.launch_context.env.get("PYTHONPATH")
        if python_path:
            python_paths.append(python_path)

        # Set new PYTHONPATH to launch context environments
        self.launch_context.env["PYTHONPATH"] = os.pathsep.join(python_paths)
