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
    PROFILE_NUMBER = 16

    def get_fusion_profile_name(self) -> str:
        """usually set to 'Default', unless FUSION16_PROFILE is set"""
        return os.getenv(f"FUSION{self.PROFILE_NUMBER}_PROFILE", "Default")

    def get_profile_source(self) -> Path:
        """Get the Fusion preferences (profile) location.
        Check https://www.steakunderwater.com/VFXPedia/96.0.243.189/indexad6a.html?title=Per-User_Preferences_and_Paths for reference.
        """
        fusion_profile = self.get_fusion_profile_name()
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
            prefs_source = Path(os.getenv("AppData"), fusion_prefs_path)
        elif platform.system() == "Darwin":
            prefs_source = Path("~/Library/Application Support/", fusion_prefs_path).expanduser()
        elif platform.system() == "Linux":
            prefs_source = Path("~/.fusion", fusion_prefs_path).expanduser()
        self.log.info(f"Got Fusion prefs file: {prefs_source}")
        return prefs_source

    def get_copy_fusion_prefs_settings(self):
        """Get copy prefserences options from the global application settings"""
        copy_fusion_settings = (
            self.data
            ["project_settings"]
            ["fusion"]
            .get("copy_fusion_settings", {})
        )
        if not copy_fusion_settings:
            self.log.error("Copy prefs settings not found")
        copy_status = copy_fusion_settings.get("copy_status", False)
        force_sync = copy_fusion_settings.get("force_sync", False)
        copy_path = copy_fusion_settings.get("copy_path") or None
        if copy_path:
            copy_path = Path(copy_path).expanduser()
        return copy_status, copy_path, force_sync

    def copy_existing_prefs(self, copy_from: Path, copy_to: Path, force_sync: bool) -> None:
        """On the first Fusion launch copy the Fusion profile to the working directory.
        If the Openpype profile folder exists, skip copying, unless Force sync is checked.
        If the prefs were not copied on the first launch, clean Fusion profile 
        will be created in fusion_profile_dir.
        """
        if copy_to.exists() and not force_sync:
            self.log.info("Local Fusion preferences folder exists, skipping profile copy")
            return
        self.log.info(f"Starting copying Fusion preferences")
        self.log.info(f"force_sync option is set to {force_sync}")
        dest_folder = copy_to / self.get_fusion_profile_name()
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
        self.launch_context.env[f"FUSION{self.PROFILE_NUMBER}_PYTHON36_HOME"] = py3_dir

        # Add custom Fusion Master Prefs and the temporary profile directory variables
        # to customize Fusion to define where it can read custom scripts and tools from
        self.log.info(f"Setting OPENPYPE_FUSION: {FUSION_HOST_DIR}")
        self.launch_context.env["OPENPYPE_FUSION"] = FUSION_HOST_DIR

        copy_status, fusion_profile_dir, force_sync = self.get_copy_fusion_prefs_settings()
        if copy_status:
            prefs_source = self.get_profile_source()
            self.copy_existing_prefs(prefs_source, fusion_profile_dir, force_sync)
        fusion_profile_dir_variable = f"FUSION{self.PROFILE_NUMBER}_PROFILE_DIR"
        master_prefs_variable = f"FUSION{self.PROFILE_NUMBER}_MasterPrefs"
        master_prefs = Path(FUSION_HOST_DIR, "deploy", "fusion_shared.prefs")
        self.log.info(f"Setting {fusion_profile_dir_variable}: {fusion_profile_dir}")
        self.launch_context.env[fusion_profile_dir_variable] = str(fusion_profile_dir)
        self.log.info(f"Setting {master_prefs_variable}: {master_prefs}")
        self.launch_context.env[master_prefs_variable] = str(master_prefs)
