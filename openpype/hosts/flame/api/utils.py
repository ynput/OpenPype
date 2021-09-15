#! python3

"""
Resolve's tools for setting environment
"""

import os
import shutil
from . import HOST_DIR
from openpype.api import Logger
log = Logger().get_logger(__name__)


def _sync_utility_scripts(env=None):
    """ Synchronizing basic utlility scripts for resolve.

    To be able to run start OpenPype within Flame we have to copy
    all utility_scripts and additional FLAME_SCRIPT_DIR into
    `/opt/Autodesk/shared/python`. This will be always synchronizing those
    folders.
    """
    if not env:
        env = os.environ

    # initiate inputs
    scripts = {}
    fsd_env = env.get("FLAME_SCRIPT_DIR", "")
    flame_shared_dir = "/opt/Autodesk/shared/python"

    fsd_paths = [os.path.join(
        HOST_DIR,
        "utility_scripts"
    )]

    # collect script dirs
    log.info(f"FLAME_SCRIPT_DIR: `{fsd_env}`")
    log.info(f"fsd_paths: `{fsd_paths}`")

    # add application environment setting for FLAME_SCRIPT_DIR
    # to script path search
    for _dirpath in fsd_env.split(os.pathsep):
        if not os.path.isdir(_dirpath):
            log.warning(f"Path is not a valid dir: `{_dirpath}`")
            continue
        fsd_paths.append(_dirpath)

    # collect scripts from dirs
    for path in fsd_paths:
        scripts.update({path: os.listdir(path)})

    log.info(f"Additional Flame script paths: `{fsd_paths}`")
    log.info(f"Flame Scripts: `{scripts}`")

    # make sure no script file is in folder
    if next(iter(os.listdir(flame_shared_dir)), None):
        for s in os.listdir(flame_shared_dir):
            path = os.path.join(flame_shared_dir, s)
            log.info(f"Removing `{path}`...")
            if os.path.isdir(path):
                shutil.rmtree(path, onerror=None)
            else:
                os.remove(path)

    # copy scripts into Resolve's utility scripts dir
    for dirpath, scriptlist in scripts.items():
        # directory and scripts list
        for _script in scriptlist:
            # script in script list
            src = os.path.join(dirpath, _script)
            dst = os.path.join(flame_shared_dir, _script)
            log.info(f"Copying `{src}` to `{dst}`...")
            if os.path.isdir(src):
                shutil.copytree(
                    src, dst, symlinks=False,
                    ignore=None, ignore_dangling_symlinks=False
                )
            else:
                shutil.copy2(src, dst)


def setup(env=None):
    """ Wrapper installer started from pype.hooks.resolve.FlamePrelaunch()
    """
    if not env:
        env = os.environ

    # synchronize resolve utility scripts
    _sync_utility_scripts(env)

    log.info("Flame OpenPype wrapper has been installed")
