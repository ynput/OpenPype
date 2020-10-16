#! python3

"""
Fusion tools for setting environment
"""

import os
import shutil

from pypeapp import Logger

log = Logger().get_logger(__name__, "fusion")


def _sync_utility_scripts(env=None):
    """ Synchronizing basic utlility scripts for resolve.

    To be able to run scripts from inside `Fusion/Workspace/Scripts` menu
    all scripts has to be accessible from defined folder.
    """
    if not env:
        env = os.environ

    # initiate inputs
    scripts = {}
    us_env = env.get("FUSION_UTILITY_SCRIPTS_SOURCE_DIR")
    us_dir = env.get("FUSION_UTILITY_SCRIPTS_DIR", "")
    us_paths = [os.path.join(
        os.path.dirname(__file__),
        "utility_scripts"
    )]

    # collect script dirs
    if us_env:
        log.info(f"Utility Scripts Env: `{us_env}`")
        us_paths = us_env.split(
            os.pathsep) + us_paths

    # collect scripts from dirs
    for path in us_paths:
        scripts.update({path: os.listdir(path)})

    log.info(f"Utility Scripts Dir: `{us_paths}`")
    log.info(f"Utility Scripts: `{scripts}`")

    # make sure no script file is in folder
    if next((s for s in os.listdir(us_dir)), None):
        for s in os.listdir(us_dir):
            path = os.path.normpath(
                os.path.join(us_dir, s))
            log.info(f"Removing `{path}`...")

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

            log.info(f"Copying `{src}` to `{dst}`...")

            # copy file or directory from our folders to fusion's folder
            if not os.path.isdir(src):
                shutil.copy2(src, dst)
            else:
                shutil.copytree(src, dst)


def setup(env=None):
    """ Wrapper installer started from pype.hooks.fusion.FusionPrelaunch()
    """
    if not env:
        env = os.environ

    # synchronize resolve utility scripts
    _sync_utility_scripts(env)

    log.info("Fusion Pype wrapper has been installed")
