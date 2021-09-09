import os
from openpype.lib import PreLaunchHook
from openpype_modules.ftrack import FTRACK_MODULE_DIR


class PrePython2Support(PreLaunchHook):
    """Add python ftrack api module for Python 2 to PYTHONPATH.

    Path to vendor modules is added to the beggining of PYTHONPATH.
    """

    def execute(self):
        if not self.application.use_python_2:
            return

        self.log.info("Adding Ftrack Python 2 packages to PYTHONPATH.")

        # Prepare vendor dir path
        python_2_vendor = os.path.join(FTRACK_MODULE_DIR, "python2_vendor")

        # Add Python 2 modules
        python_paths = [
            # `python-ftrack-api`
            os.path.join(python_2_vendor, "ftrack-python-api", "source"),
            # `arrow`
            os.path.join(python_2_vendor, "arrow"),
            # `builtins` from `python-future`
            # - `python-future` is strict Python 2 module that cause crashes
            #   of Python 3 scripts executed through OpenPype (burnin script etc.)
            os.path.join(python_2_vendor, "builtins"),
            # `backports.functools_lru_cache`
            os.path.join(
                python_2_vendor, "backports.functools_lru_cache"
            )
        ]

        # Load PYTHONPATH from current launch context
        python_path = self.launch_context.env.get("PYTHONPATH")
        if python_path:
            python_paths.append(python_path)

        # Set new PYTHONPATH to launch context environments
        self.launch_context.env["PYTHONPATH"] = os.pathsep.join(python_paths)
