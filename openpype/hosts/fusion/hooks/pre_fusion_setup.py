import os
import shutil

import openpype.hosts.fusion
from openpype.lib import PreLaunchHook, ApplicationLaunchFailed


class FusionPrelaunch(PreLaunchHook):
    """
    This hook will check if current workfile path has Fusion
    project inside.
    """
    app_groups = ["fusion"]

    def execute(self):
        # making sure python 3.6 is installed at provided path
        py36_dir = self.launch_context.env.get("PYTHON36")
        if not py36_dir:
            raise ApplicationLaunchFailed(
                "Required environment variable \"PYTHON36\" is not set."
                "\n\nFusion implementation requires to have"
                " installed Python 3.6"
            )

        py36_dir = os.path.normpath(py36_dir)
        if not os.path.isdir(py36_dir):
            raise ApplicationLaunchFailed(
                "Python 3.6 is not installed at the provided path.\n"
                "Either make sure the environments in fusion settings has"
                " 'PYTHON36' set corectly or make sure Python 3.6 is installed"
                f" in the given path.\n\nPYTHON36: {py36_dir}"
            )
        self.log.info(f"Path to Fusion Python folder: '{py36_dir}'...")
        self.launch_context.env["PYTHON36"] = py36_dir

        utility_dir = self.launch_context.env.get("FUSION_UTILITY_SCRIPTS_DIR")
        if not utility_dir:
            raise ApplicationLaunchFailed(
                "Required Fusion utility script dir environment variable"
                " \"FUSION_UTILITY_SCRIPTS_DIR\" is not set."
            )

        # setting utility scripts dir for scripts syncing
        utility_dir = os.path.normpath(utility_dir)
        if not os.path.isdir(utility_dir):
            raise ApplicationLaunchFailed(
                "Fusion utility script dir does not exist. Either make sure "
                "the environments in fusion settings has"
                " 'FUSION_UTILITY_SCRIPTS_DIR' set correctly or reinstall "
                f"Fusion.\n\nFUSION_UTILITY_SCRIPTS_DIR: '{utility_dir}'"
            )

        self._sync_utility_scripts(self.launch_context.env)
        self.log.info("Fusion Pype wrapper has been installed")

    def _sync_utility_scripts(self, env):
        """ Synchronizing basic utlility scripts for resolve.

        To be able to run scripts from inside `Fusion/Workspace/Scripts` menu
        all scripts has to be accessible from defined folder.
        """
        if not env:
            env = {k: v for k, v in os.environ.items()}

        # initiate inputs
        scripts = {}
        us_env = env.get("FUSION_UTILITY_SCRIPTS_SOURCE_DIR")
        us_dir = env.get("FUSION_UTILITY_SCRIPTS_DIR", "")
        us_paths = [os.path.join(
            os.path.dirname(os.path.abspath(openpype.hosts.fusion.__file__)),
            "utility_scripts"
        )]

        # collect script dirs
        if us_env:
            self.log.info(f"Utility Scripts Env: `{us_env}`")
            us_paths = us_env.split(
                os.pathsep) + us_paths

        # collect scripts from dirs
        for path in us_paths:
            scripts.update({path: os.listdir(path)})

        self.log.info(f"Utility Scripts Dir: `{us_paths}`")
        self.log.info(f"Utility Scripts: `{scripts}`")

        # make sure no script file is in folder
        if next((s for s in os.listdir(us_dir)), None):
            for s in os.listdir(us_dir):
                path = os.path.normpath(
                    os.path.join(us_dir, s))
                self.log.info(f"Removing `{path}`...")

                # remove file or directory if not in our folders
                if not os.path.isdir(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)

        # copy scripts into Resolve's utility scripts dir
        for d, sl in scripts.items():
            # directory and scripts list
            for s in sl:
                # script in script list
                src = os.path.normpath(os.path.join(d, s))
                dst = os.path.normpath(os.path.join(us_dir, s))

                self.log.info(f"Copying `{src}` to `{dst}`...")

                # copy file or directory from our folders to fusion's folder
                if not os.path.isdir(src):
                    shutil.copy2(src, dst)
                else:
                    shutil.copytree(src, dst)
