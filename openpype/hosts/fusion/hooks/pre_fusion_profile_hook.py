import os
import shutil
import platform
from pathlib import Path
from openpype.lib import PreLaunchHook
from openpype.hosts.fusion import FUSION_PROFILE_VERSION as VERSION


class FusionCopyPrefsPrelaunch(PreLaunchHook):
    """Prepares local Fusion profile directory, copies existing Fusion profile
    """

    app_groups = ["fusion"]

    def get_fusion_profile_name(self) -> str:
        """usually set to 'Default', unless FUSION16_PROFILE is set"""
        return os.getenv(f"FUSION{VERSION}_PROFILE", "Default")

    def get_profile_source(self) -> Path:
        """Get the Fusion preferences (profile) location.
        Check Per-User_Preferences_and_Paths on VFXpedia for reference.
        """
        fusion_profile = self.get_fusion_profile_name()
        fusion_var_prefs_dir = os.getenv(f"FUSION{VERSION}_PROFILE_DIR")

        # if FUSION16_PROFILE_DIR variable exists
        if fusion_var_prefs_dir and Path(fusion_var_prefs_dir).is_dir():
            fusion_prefs_dir = Path(fusion_var_prefs_dir, fusion_profile)
            self.log.info(
                f"Local Fusion prefs environment is set to {fusion_prefs_dir}"
            )
            return fusion_prefs_dir
        # otherwise get the profile folder from default location
        fusion_prefs_dir = f"Blackmagic Design/Fusion/Profiles/{fusion_profile}"  # noqa
        if platform.system() == "Windows":
            prefs_source = Path(os.getenv("AppData"), fusion_prefs_dir)
        elif platform.system() == "Darwin":
            prefs_source = Path(
                "~/Library/Application Support/", fusion_prefs_dir
            ).expanduser()
        elif platform.system() == "Linux":
            prefs_source = Path("~/.fusion", fusion_prefs_dir).expanduser()
        self.log.info(f"Got Fusion prefs file: {prefs_source}")
        return prefs_source

    def get_copy_fusion_prefs_settings(self):
        """Get copy preferences options from the global application settings"""
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

    def copy_existing_prefs(
        self, copy_from: Path, copy_to: Path, force_sync: bool
    ) -> None:
        """On the first Fusion launch copy the contents of Fusion profile
        directory to the working predefined location. If the Openpype profile
        folder exists, skip copying, unless re-sync is checked.
        If the prefs were not copied on the first launch,
        clean Fusion profile will be created in fusion_profile_dir.
        """
        if copy_to.exists() and not force_sync:
            self.log.info(
                "Local Fusion preferences folder exists, skipping profile copy"
            )
            return
        self.log.info(f"Starting copying Fusion preferences")
        self.log.info(f"force_sync option is set to {force_sync}")
        dest_folder = copy_to / self.get_fusion_profile_name()
        try:
            dest_folder.mkdir(exist_ok=True, parents=True)
        except Exception:
            self.log.warn(f"Could not create folder at {dest_folder}")
            return
        if not copy_from.exists():
            self.log.warning(f"Fusion preferences not found in {copy_from}")
            return
        for file in copy_from.iterdir():
            if file.suffix in (".prefs", ".def", ".blocklist", ".fu"):
                # convert Path to str to be compatible with Python 3.6+
                shutil.copy(str(file), str(dest_folder))
        self.log.info(
            f"successfully copied preferences:\n {copy_from} to {dest_folder}"
        )

    def execute(self):
        (
            copy_status,
            fusion_profile_dir,
            force_sync,
        ) = self.get_copy_fusion_prefs_settings()

        # do a copy of Fusion profile if copy_status toggle is enabled
        if copy_status and fusion_profile_dir is not None:
            prefs_source = self.get_profile_source()
            self.copy_existing_prefs(prefs_source, fusion_profile_dir, force_sync)  # noqa

        # Add temporary profile directory variables to customize Fusion
        # to define where it can read custom scripts and tools from
        fusion_profile_dir_variable = f"FUSION{VERSION}_PROFILE_DIR"
        self.log.info(f"Setting {fusion_profile_dir_variable}: {fusion_profile_dir}")  # noqa
        self.launch_context.env[fusion_profile_dir_variable] = str(fusion_profile_dir)  # noqa