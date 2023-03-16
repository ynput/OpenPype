import os
import shutil
import platform
from pathlib import Path
from openpype.lib import PreLaunchHook
from openpype.hosts.fusion import FUSION_HOST_DIR, get_fusion_profile_number


class FusionCopyPrefsPrelaunch(PreLaunchHook):
    """Prepares local Fusion profile directory, copies existing Fusion profile
    """

    app_groups = ["fusion"]
    order = 2

    def get_fusion_profile_name(self, app_version) -> str:
        # Returns 'Default', unless FUSION16_PROFILE is set
        return os.getenv(f"FUSION{app_version}_PROFILE", "Default")

    def check_profile_variable(self, app_version) -> Path:
        # Get FUSION_PROFILE_DIR variable
        fusion_profile = self.get_fusion_profile_name(app_version)
        fusion_var_prefs_dir = os.getenv(f"FUSION{app_version}_PROFILE_DIR")

        # Check if FUSION_PROFILE_DIR exists
        if fusion_var_prefs_dir and Path(fusion_var_prefs_dir).is_dir():
            fu_prefs_dir = Path(fusion_var_prefs_dir, fusion_profile)
            self.log.info(f"{fusion_var_prefs_dir} is set to {fu_prefs_dir}")
            return fu_prefs_dir

    def get_profile_source(self, app_version) -> Path:
        """Get Fusion preferences profile location.
        See Per-User_Preferences_and_Paths on VFXpedia for reference.
        """
        fusion_profile = self.get_fusion_profile_name(app_version)
        profile_source = self.check_profile_variable(app_version)
        if profile_source:
            return profile_source
        # otherwise get default location of the profile folder
        fu_prefs_dir = f"Blackmagic Design/Fusion/Profiles/{fusion_profile}"
        if platform.system() == "Windows":
            profile_source = Path(os.getenv("AppData"), fu_prefs_dir)
        elif platform.system() == "Darwin":
            profile_source = Path(
                "~/Library/Application Support/", fu_prefs_dir
            ).expanduser()
        elif platform.system() == "Linux":
            profile_source = Path("~/.fusion", fu_prefs_dir).expanduser()
        self.log.info(f"Locating source Fusion prefs directory: {profile_source}")
        return profile_source

    def get_copy_fusion_prefs_settings(self):
        # Get copy preferences options from the global application settings

        copy_fusion_settings = self.data["project_settings"]["fusion"].get(
            "copy_fusion_settings", {}
        )
        if not copy_fusion_settings:
            self.log.error("Copy prefs settings not found")
        copy_status = copy_fusion_settings.get("copy_status", False)
        force_sync = copy_fusion_settings.get("force_sync", False)
        copy_path = copy_fusion_settings.get("copy_path") or None
        if copy_path:
            copy_path = Path(copy_path).expanduser()
        return copy_status, copy_path, force_sync

    def copy_fusion_profile(
        self, copy_from: Path, copy_to: Path, force_sync: bool
    ) -> None:
        """On the first Fusion launch copy the contents of Fusion profile
        directory to the working predefined location. If the Openpype profile
        folder exists, skip copying, unless re-sync is checked.
        If the prefs were not copied on the first launch,
        clean Fusion profile will be created in fu_profile_dir.
        """
        if copy_to.exists() and not force_sync:
            self.log.info(
                "Local Fusion preferences folder exists, skipping profile copy"
            )
            return
        self.log.info(f"Starting copying Fusion preferences")
        self.log.info(f"force_sync option is set to {force_sync}")
        try:
            copy_to.mkdir(exist_ok=True, parents=True)
        except Exception:
            self.log.warn(f"Could not create folder at {copy_to}")
            return
        if not copy_from.exists():
            self.log.warning(f"Fusion preferences not found in {copy_from}")
            return
        for file in copy_from.iterdir():
            if file.suffix in (".prefs", ".def", ".blocklist", ".fu"):
                # convert Path to str to be compatible with Python 3.6+
                shutil.copy(str(file), str(copy_to))
        self.log.info(
            f"successfully copied preferences:\n {copy_from} to {copy_to}"
        )

    def execute(self):
        (
            copy_status,
            fu_profile_dir,
            force_sync,
        ) = self.get_copy_fusion_prefs_settings()

        # Get launched application context and return correct app version
        app_data = self.launch_context.env.get("AVALON_APP_NAME")
        app_version = get_fusion_profile_number(__name__, app_data)
        fu_profile = self.get_fusion_profile_name(app_version)

        # do a copy of Fusion profile if copy_status toggle is enabled
        if copy_status and fu_profile_dir is not None:
            profile_source = self.get_profile_source(app_version)
            dest_folder = Path(fu_profile_dir, fu_profile)
            self.copy_fusion_profile(profile_source, dest_folder, force_sync)

        # Add temporary profile directory variables to customize Fusion
        # to define where it can read custom scripts and tools from
        fu_profile_dir_variable = f"FUSION{app_version}_PROFILE_DIR"
        self.log.info(f"Setting {fu_profile_dir_variable}: {fu_profile_dir}")
        self.launch_context.env[fu_profile_dir_variable] = str(fu_profile_dir)

        # Add custom Fusion Master Prefs and the temporary
        # profile directory variables to customize Fusion
        # to define where it can read custom scripts and tools from
        master_prefs_variable = f"FUSION{app_version}_MasterPrefs"
        master_prefs = Path(FUSION_HOST_DIR, "deploy", "fusion_shared.prefs")
        self.log.info(f"Setting {master_prefs_variable}: {master_prefs}")
        self.launch_context.env[master_prefs_variable] = str(master_prefs)
