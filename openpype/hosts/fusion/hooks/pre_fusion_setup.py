import os
from openpype.lib import PreLaunchHook, ApplicationLaunchFailed
from openpype.hosts.fusion import FUSION_HOST_DIR


class FusionPrelaunch(PreLaunchHook):
    """Prepares OpenPype Fusion environment

    Requires FUSION_PYTHON3_HOME to be defined in the environment for Fusion
    to point at a valid Python 3 build for Fusion. That is Python 3.3-3.10
    for Fusion 18 and Fusion 3.6 for Fusion 16 and 17.

    This also sets FUSION16_MasterPrefs to apply the fusion master prefs
    as set in openpype/hosts/fusion/deploy/fusion_shared.prefs to enable
    the OpenPype menu and force Python 3 over Python 2.

    """
    app_groups = ["fusion"]

    def execute(self):
        # making sure python 3 is installed at provided path
        # Py 3.3-3.10 for Fusion 18+ or Py 3.6 for Fu 16-17
        py3_var = "FUSION_PYTHON3_HOME"
        fusion_python3_home = self.launch_context.env.get(py3_var, "")

        self.log.info(f"Looking for Python 3 in: {fusion_python3_home}")
        for path in fusion_python3_home.split(os.pathsep):
            # Allow defining multiple paths to allow "fallback" to other
            # path. But make to set only a single path as final variable.
            py3_dir = os.path.normpath(path)
            if os.path.isdir(py3_dir):
                break
        else:
            raise ApplicationLaunchFailed(
                "Python 3 is not installed at the provided path.\n"
                "Make sure the environment in fusion settings has "
                "'FUSION_PYTHON3_HOME' set correctly and make sure "
                "Python 3 is installed in the given path."
                f"\n\nPYTHON36: {fusion_python3_home}"
            )

        self.log.info(f"Setting {py3_var}: '{py3_dir}'...")
        self.launch_context.env[py3_var] = py3_dir

        # Fusion 18+ requires FUSION_PYTHON3_HOME to also be on PATH
        self.launch_context.env["PATH"] += ";" + py3_dir

        # Fusion 16 and 17 use FUSION16_PYTHON36_HOME instead of
        # FUSION_PYTHON3_HOME and will only work with a Python 3.6 version
        # TODO: Detect Fusion version to only set for specific Fusion build
        self.launch_context.env["FUSION16_PYTHON36_HOME"] = py3_dir

        # Add our Fusion Master Prefs which is the only way to customize
        # Fusion to define where it can read custom scripts and tools from
        self.log.info(f"Setting OPENPYPE_FUSION: {FUSION_HOST_DIR}")
        self.launch_context.env["OPENPYPE_FUSION"] = FUSION_HOST_DIR

        pref_var = "FUSION16_MasterPrefs"   # used by Fusion 16, 17 and 18
        prefs = os.path.join(FUSION_HOST_DIR, "deploy", "fusion_shared.prefs")
        self.log.info(f"Setting {pref_var}: {prefs}")
        self.launch_context.env[pref_var] = prefs
