import os
from openpype.lib.applications import (
    PreLaunchHook,
    LaunchTypes,
    ApplicationLaunchFailed,
)
from openpype.hosts.fusion import (
    FUSION_HOST_DIR,
    FUSION_VERSIONS_DICT,
    get_fusion_version,
)


class FusionPrelaunch(PreLaunchHook):
    """
    Prepares OpenPype Fusion environment.
    Requires correct Python home variable to be defined in the environment
    settings for Fusion to point at a valid Python 3 build for Fusion.
    Python3 versions that are supported by Fusion:
    Fusion 9, 16, 17 : Python 3.6
    Fusion 18        : Python 3.6 - 3.10
    """

    app_groups = {"fusion"}
    order = 1
    launch_types = {LaunchTypes.local}

    def execute(self):
        # making sure python 3 is installed at provided path
        # Py 3.3-3.10 for Fusion 18+ or Py 3.6 for Fu 16-17
        app_data = self.launch_context.env.get("AVALON_APP_NAME")
        app_version = get_fusion_version(app_data)
        if not app_version:
            raise ApplicationLaunchFailed(
                "Fusion version information not found in System settings.\n"
                "The key field in the 'applications/fusion/variants' should "
                "consist a number, corresponding to major Fusion version."
            )
        py3_var, _ = FUSION_VERSIONS_DICT[app_version]
        fusion_python3_home = self.launch_context.env.get(py3_var, "")

        for path in fusion_python3_home.split(os.pathsep):
            # Allow defining multiple paths, separated by os.pathsep,
            # to allow "fallback" to other path.
            # But make to set only a single path as final variable.
            py3_dir = os.path.normpath(path)
            if os.path.isdir(py3_dir):
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
        if app_version >= 18:
            self.launch_context.env["PATH"] += os.pathsep + py3_dir

        self.launch_context.env[py3_var] = py3_dir

        # for hook installing PySide2
        self.data["fusion_python3_home"] = py3_dir

        self.log.info(f"Setting OPENPYPE_FUSION: {FUSION_HOST_DIR}")
        self.launch_context.env["OPENPYPE_FUSION"] = FUSION_HOST_DIR
