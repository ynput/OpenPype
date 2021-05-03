import os
from openpype.lib import PreLaunchHook


class PrePython2Vendor(PreLaunchHook):
    """Prepend python 2 dependencies for py2 hosts."""
    order = 10

    def execute(self):
        if not self.application.use_python_2:
            return

        # Prepare vendor dir path
        self.log.info("adding global python 2 vendor")
        pype_root = os.getenv("OPENPYPE_REPOS_ROOT")
        python_2_vendor = os.path.join(
            pype_root,
            "openpype",
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
