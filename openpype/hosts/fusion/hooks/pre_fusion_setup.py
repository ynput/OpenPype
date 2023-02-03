import os
import shutil
import platform
from pathlib import Path
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
    OPENPYPE_FUSION_PROFILE_DIR = "~/.openpype/hosts/fusion/prefs"
    PROFILE_NUMBER = 16

    def get_fusion_profile(self) -> str:
        return os.getenv(f"FUSION{self.PROFILE_NUMBER}_PROFILE", "Default")

    def get_profile_source(self) -> Path:
        fusion_profile = self.get_fusion_profile()
        fusion_var_prefs_dir = os.getenv(f"FUSION{self.PROFILE_NUMBER}_PROFILE_DIR")

        # if FUSION16_PROFILE_DIR variable exists, return the profile filepath
        if fusion_var_prefs_dir and Path(fusion_var_prefs_dir).is_dir():
            fusion_prefs_dir = Path(fusion_var_prefs_dir, fusion_profile)
            self.log.info(f"Local Fusion prefs environment is set to {fusion_prefs_dir}")
            fusion_prefs_filepath = fusion_prefs_dir / "Fusion.prefs"
            return fusion_prefs_filepath
        
        # otherwise get the profile from default prefs location 
        fusion_prefs_path = f"Blackmagic Design/Fusion/Profiles/{fusion_profile}/Fusion.prefs"
        if platform.system() == "Windows":
            prefs_source = Path(os.getenv("AppData")) / fusion_prefs_path
        elif platform.system() == "Darwin":
            prefs_source = Path("~/Library/Application Support/", fusion_prefs_path).expanduser()
        elif platform.system() == "Linux":
            prefs_source = Path("~/.fusion", fusion_prefs_path).expanduser()
            
        return prefs_source

    def copy_existing_prefs(self, copy_from: Path, copy_to: Path) -> None:
        dest_folder = copy_to / self.get_fusion_profile()
        dest_folder.mkdir(exist_ok=True, parents=True)        
        if not copy_from.exists():
            self.log.warning(f"Fusion preferences file not found in {copy_from}")
            return
        shutil.copy(str(copy_from), str(dest_folder)) # compatible with Python >= 3.6
        self.log.info(f"successfully copied preferences:\n {copy_from} to {dest_folder}")
        
    def execute(self):
        # making sure python 3 is installed at provided path
        # Py 3.3-3.10 for Fusion 18+ or Py 3.6 for Fu 16-17

        py3_var = "FUSION_PYTHON3_HOME"
        fusion_python3_home = self.launch_context.env.get(py3_var, "")

        for path in fusion_python3_home.split(os.pathsep):
            # Allow defining multiple paths, separated by os.pathsep, to allow "fallback" to other
            # path. But make to set only a single path as final variable.
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

        # Add custom Fusion Master Prefs and the temporary profile directory variables to customize
        # Fusion to define where it can read custom scripts and tools from
        self.log.info(f"Setting OPENPYPE_FUSION: {FUSION_HOST_DIR}")
        self.launch_context.env["OPENPYPE_FUSION"] = FUSION_HOST_DIR

        profile_dir_var = "FUSION16_PROFILE_DIR"   # used by Fusion 16, 17 and 18
        pref_var = "FUSION16_MasterPrefs"   # used by Fusion 16, 17 and 18
        op_profile_dir = Path(self.OPENPYPE_FUSION_PROFILE_DIR).expanduser()
        op_master_prefs = Path(FUSION_HOST_DIR, "deploy", "fusion_shared.prefs")
        prefs_source = self.get_profile_source()
        self.log.info(f"Got Fusion prefs file: {prefs_source}")

        # now copy the default Fusion profile to a working directory
        # only if the openpype profile folder does not exist
        if not op_profile_dir.exists():
            self.copy_existing_prefs(prefs_source, op_profile_dir)
        self.log.info(f"Setting {profile_dir_var}: {op_profile_dir}")
        self.launch_context.env[profile_dir_var] = str(op_profile_dir)
        self.log.info(f"Setting {pref_var}: {op_master_prefs}")
        self.launch_context.env[pref_var] = str(op_master_prefs)
