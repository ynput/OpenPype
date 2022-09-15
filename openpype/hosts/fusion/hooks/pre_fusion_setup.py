import os
from openpype.lib import PreLaunchHook, ApplicationLaunchFailed
from openpype.hosts.fusion import HOST_DIR


class FusionPrelaunch(PreLaunchHook):
    """
    This hook will check if current workfile path has Fusion
    project inside.
    """
    app_groups = ["fusion"]

    def execute(self):
        # making sure python 3.6 is installed at provided path
        py36_var = "FUSION16_PYTHON36_HOME"
        fusion_python36_home = self.launch_context.env.get(py36_var, "")

        self.log.info(f"Looking for Python 3.6 in: {fusion_python36_home}")
        for path in fusion_python36_home.split(os.pathsep):
            # Allow defining multiple paths to allow "fallback" to other
            # path. But make to set only a single path as final variable.
            py36_dir = os.path.normpath(path)
            if os.path.isdir(py36_dir):
                break
        else:
            raise ApplicationLaunchFailed(
                "Python 3.6 is not installed at the provided path.\n"
                "Either make sure the environments in fusion settings has"
                " 'PYTHON36' set corectly or make sure Python 3.6 is installed"
                f" in the given path.\n\nPYTHON36: {fusion_python36_home}"
            )

        self.log.info(f"Setting {py36_var}: '{py36_dir}'...")
        self.launch_context.env[py36_var] = py36_dir

        # TODO: Set this for EITHER Fu16-17 OR Fu18+, don't do both
        # Fusion 18+ does not look in FUSION16_PYTHON36_HOME anymore
        # but instead uses FUSION_PYTHON3_HOME and requires the Python to
        # be available on PATH to work. So let's enforce that for now.
        self.launch_context.env["FUSION_PYTHON3_HOME"] = py36_dir
        self.launch_context.env["PATH"] += ";" + py36_dir

        # Add our Fusion Master Prefs which is the only way to customize
        # Fusion to define where it can read custom scripts and tools from
        self.log.info(f"Setting OPENPYPE_FUSION: {HOST_DIR}")
        self.launch_context.env["OPENPYPE_FUSION"] = HOST_DIR

        pref_var = "FUSION16_MasterPrefs"   # used by both Fu16 and Fu17
        prefs = os.path.join(HOST_DIR, "deploy", "fusion_shared.prefs")
        self.log.info(f"Setting {pref_var}: {prefs}")
        self.launch_context.env[pref_var] = prefs
