from pathlib import Path

from openpype.lib import PreLaunchHook
from openpype.hosts.openrv import OPENRV_ROOT_DIR


class PreSetupOpenRV(PreLaunchHook):
    """Pre-hook for openrv"""
    app_groups = ["openrv"]

    def execute(self):
        root = Path(OPENRV_ROOT_DIR)
        startup = root / "startup"
        packages_dir = startup / "Packages"

        # TODO: Auto deployment should not be this hacky
        # Redeploy the source packages to zips to auto-update
        # during development of OpenRV
        import zipfile
        for package_name in ["comments", "openpype_menus-1.0"]:
            package_src = startup / "pkgs_source" / package_name
            package_dest = packages_dir / "{}.zip".format(package_name)
            print(f"Writing: {package_dest}")
            with zipfile.ZipFile(package_dest, mode="w") as zip:
                for filepath in package_src.iterdir():
                    if not filepath.is_file():
                        continue

                    zip.write(filepath,
                              arcname=filepath.name)

        # TODO: Make sure we don't override a full studios RV_SUPPORT_PATH
        print("Setting RV_SUPPORT_PATH", startup)
        self.launch_context.env["RV_SUPPORT_PATH"] = str(startup)

        # TODO: OpenRV does write files into RV_SUPPORT_PATH during runtime
        #   so we should actually not deploy that as a path inside OP deploy
        #   to avoid openpype checksum validation issues, etc. but for now
        #   it helps running from code to run the integration for development
