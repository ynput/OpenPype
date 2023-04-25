import os
import shutil
import tempfile
from pathlib import Path

from openpype.lib import PreLaunchHook
from openpype.hosts.openrv import OPENRV_ROOT_DIR
from openpype.lib.execute import run_subprocess


class PreSetupOpenRV(PreLaunchHook):
    """Pre-hook for openrv"""
    app_groups = ["openrv"]

    def execute(self):

        executable = self.application.find_executable()
        if not executable:
            self.log.error("Unable to find executable for RV.")
            return

        # We use the `rvpkg` executable next to the `rv` executable to
        # install and opt-in to the OpenPype plug-in packages
        rvpkg = Path(os.path.dirname(str(executable))) / "rvpkg"
        packages_src_folder = Path(OPENRV_ROOT_DIR) / "startup" / "pkgs_source"

        # TODO: Are we sure we want to deploy the addons into a temporary
        #   RV_SUPPORT_PATH on each launch. This would create redundant temp
        #   files that remain on disk but it does allow us to ensure RV is
        #   now running with the correct version of the RV packages of this
        #   current running OpenPype version
        op_support_path = Path(tempfile.mkdtemp(
            prefix="openpype_rv_support_path_"
        ))

        # Write the OpenPype RV package zips directly to the support path
        # Packages/ folder then we don't need to `rvpkg -add` them afterwards
        packages_dest_folder = op_support_path / "Packages"
        packages_dest_folder.mkdir(exist_ok=True)
        packages = ["comments", "openpype_menus", "openpype_scripteditor"]
        for package_name in packages:
            package_src = packages_src_folder / package_name
            package_dest = packages_dest_folder / "{}.zip".format(package_name)

            self.log.debug(f"Writing: {package_dest}")
            shutil.make_archive(str(package_dest), "zip", str(package_src))

        # Install and opt-in the OpenPype RV packages
        install_args = [rvpkg, "-only", op_support_path, "-install"]
        install_args.extend(packages)
        optin_args = [rvpkg, "-only", op_support_path, "-optin"]
        optin_args.extend(packages)
        run_subprocess(install_args, logger=self.log)
        run_subprocess(optin_args, logger=self.log)

        self.log.debug(f"Adding RV_SUPPORT_PATH: {op_support_path}")
        support_path = self.launch_context.env.get("RV_SUPPORT_PATH")
        if support_path:
            support_path = os.pathsep.join([support_path,
                                            str(op_support_path)])
        else:
            support_path = str(op_support_path)
        self.log.debug(f"Setting RV_SUPPORT_PATH: {support_path}")
        self.launch_context.env["RV_SUPPORT_PATH"] = support_path
