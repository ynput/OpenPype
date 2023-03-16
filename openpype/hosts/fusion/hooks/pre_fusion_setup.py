import os
from openpype.lib import PreLaunchHook, ApplicationLaunchFailed
from openpype.hosts.fusion import (
    FUSION_HOST_DIR,
    get_fusion_profile_number,
)


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
    order = 1

    def execute(self):
        # making sure python 3 is installed at provided path
        # Py 3.3-3.10 for Fusion 18+ or Py 3.6 for Fu 16-17
        app_data = self.launch_context.env.get("AVALON_APP_NAME")
        app_version = get_fusion_profile_number(__name__, app_data)
        if not app_version:
            raise ApplicationLaunchFailed(
                "Fusion version information not found in System settings.\n"
                "The key field in the 'applications/fusion/variants' "
                "should consist a number, corresponding to the Fusion version"
            )

        py3_var = "FUSION_PYTHON3_HOME"
        fusion_python3_home = self.launch_context.env.get(py3_var, "")

        for path in fusion_python3_home.split(os.pathsep):
            # Allow defining multiple paths, separated by os.pathsep,
            # to allow "fallback" to other path.
            # But make to set only a single path as final variable.
            py3_dir = os.path.normpath(path)
            if os.path.isdir(py3_dir):
                self.log.info(f"Looking for Python 3 in: {py3_dir}")
                break
        else:
            raise ApplicationLaunchFailed(
                "Python 3 is not installed at the provided path.\n"
                "Make sure the environment in fusion settings has "
                "'FUSION_PYTHON3_HOME' set correctly and make sure "
                "Python 3 is installed in the given path."
                f"\n\nPYTHON PATH: {fusion_python3_home}"
            )

        self.log.info(f"Setting {py3_var}: '{py3_dir}'...")
        self.launch_context.env[py3_var] = py3_dir

        # Fusion 18+ requires FUSION_PYTHON3_HOME to also be on PATH
        self.launch_context.env["PATH"] += ";" + py3_dir

        # Fusion 16 and 17 use FUSION16_PYTHON36_HOME instead of
        # FUSION_PYTHON3_HOME and will only work with a Python 3.6 version
        # TODO: Detect Fusion version to only set for specific Fusion build
        if app_version == 9:
            self.launch_context.env[f"FUSION_PYTHON36_HOME"] = py3_dir
        elif app_version == 16:
            self.launch_context.env[
                f"FUSION{app_version}_PYTHON36_HOME"
            ] = py3_dir

        self.log.info(f"Setting OPENPYPE_FUSION: {FUSION_HOST_DIR}")
        self.launch_context.env["OPENPYPE_FUSION"] = FUSION_HOST_DIR
