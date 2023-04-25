import os
import shutil
from pathlib import Path

from openpype.lib import PreLaunchHook
from openpype.hosts.openrv import OPENRV_ROOT_DIR


class PreSetupOpenRV(PreLaunchHook):
    """Pre-hook for openrv"""
    app_groups = ["openrv"]

    def execute(self):
        root = Path(OPENRV_ROOT_DIR)
        startup = root / "startup"
        startup_packages = startup / "Packages"
        startup_python = startup / "Python"

        # Ensure folder exists
        startup_python.mkdir(exist_ok=True)

        # TODO: Auto deployment should not be this hacky
        # Redeploy the source packages to zips to auto-update
        # during development of OpenRV
        import zipfile
        for package_name in ["comments",
                             "openpype_menus-1.0",
                             "openpype_scripteditor"]:
            package_src = startup / "pkgs_source" / package_name
            package_dest = startup_packages / "{}.zip".format(package_name)
            self.log.info(f"Writing: {package_dest}")
            with zipfile.ZipFile(package_dest, mode="w") as zip:
                for filepath in package_src.iterdir():
                    if not filepath.is_file():
                        continue

                    zip.write(filepath,
                              arcname=filepath.name)

                    if filepath.suffix == ".py":
                        # Include it in Python subfolder where OpenRV deploys
                        # the files after first install (and does not update
                        # after)
                        self.log.info(
                            f"Copying {filepath} to folder {startup_python}"
                        )
                        shutil.copy(filepath, startup_python)

        self.log.debug(f"Adding RV_SUPPORT_PATH: {startup}")
        support_path = self.launch_context.env.get("RV_SUPPORT_PATH")
        if support_path:
            support_path = os.pathsep.join([support_path, str(startup)])
        else:
            support_path = str(startup)
        self.log.debug(f"Setting RV_SUPPORT_PATH: {support_path}")
        self.launch_context.env["RV_SUPPORT_PATH"] = support_path

        # TODO: OpenRV does write files into RV_SUPPORT_PATH during runtime
        #   so we should actually not deploy that as a path inside OP deploy
        #   to avoid openpype checksum validation issues, etc. but for now
        #   it helps running from code to run the integration for development
