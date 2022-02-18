"""
Flame utils for syncing scripts
"""

import os
import shutil
from openpype.api import Logger
log = Logger.get_logger(__name__)


def _sync_utility_scripts(env=None):
    """ Synchronizing basic utlility scripts for flame.

    To be able to run start OpenPype within Flame we have to copy
    all utility_scripts and additional FLAME_SCRIPT_DIR into
    `/opt/Autodesk/shared/python`. This will be always synchronizing those
    folders.
    """
    from .. import HOST_DIR

    env = env or os.environ

    # initiate inputs
    scripts = {}
    fsd_env = env.get("FLAME_SCRIPT_DIRS", "")
    flame_shared_dir = "/opt/Autodesk/shared/python"

    fsd_paths = [os.path.join(
        HOST_DIR,
        "api",
        "utility_scripts"
    )]

    # collect script dirs
    log.info("FLAME_SCRIPT_DIRS: `{fsd_env}`".format(**locals()))
    log.info("fsd_paths: `{fsd_paths}`".format(**locals()))

    # add application environment setting for FLAME_SCRIPT_DIR
    # to script path search
    for _dirpath in fsd_env.split(os.pathsep):
        if not os.path.isdir(_dirpath):
            log.warning("Path is not a valid dir: `{_dirpath}`".format(
                **locals()))
            continue
        fsd_paths.append(_dirpath)

    # collect scripts from dirs
    for path in fsd_paths:
        scripts.update({path: os.listdir(path)})

    remove_black_list = []
    for _k, s_list in scripts.items():
        remove_black_list += s_list

    log.info("remove_black_list: `{remove_black_list}`".format(**locals()))
    log.info("Additional Flame script paths: `{fsd_paths}`".format(**locals()))
    log.info("Flame Scripts: `{scripts}`".format(**locals()))

    # make sure no script file is in folder
    if next(iter(os.listdir(flame_shared_dir)), None):
        for _itm in os.listdir(flame_shared_dir):
            skip = False

            # skip all scripts and folders which are not maintained
            if _itm not in remove_black_list:
                skip = True

            # do not skip if pyc in extension
            if not os.path.isdir(_itm) and "pyc" in os.path.splitext(_itm)[-1]:
                skip = False

            # continue if skip in true
            if skip:
                continue

            path = os.path.join(flame_shared_dir, _itm)
            log.info("Removing `{path}`...".format(**locals()))

            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, onerror=None)
                else:
                    os.remove(path)
            except PermissionError as msg:
                log.warning(
                    "Not able to remove: `{}`, Problem with: `{}`".format(
                        path,
                        msg
                    )
                )

    # copy scripts into Resolve's utility scripts dir
    for dirpath, scriptlist in scripts.items():
        # directory and scripts list
        for _script in scriptlist:
            # script in script list
            src = os.path.join(dirpath, _script)
            dst = os.path.join(flame_shared_dir, _script)
            log.info("Copying `{src}` to `{dst}`...".format(**locals()))

            try:
                if os.path.isdir(src):
                    shutil.copytree(
                        src, dst, symlinks=False,
                        ignore=None, ignore_dangling_symlinks=False
                    )
                else:
                    shutil.copy2(src, dst)
            except (PermissionError, FileExistsError) as msg:
                log.warning(
                    "Not able to coppy to: `{}`, Problem with: `{}`".format(
                        dst,
                        msg
                    )
                )


def setup(env=None):
    """ Wrapper installer started from
    `flame/hooks/pre_flame_setup.py`
    """
    env = env or os.environ

    # synchronize resolve utility scripts
    _sync_utility_scripts(env)

    log.info("Flame OpenPype wrapper has been installed")


def get_flame_version():
    import flame

    return {
        "full": flame.get_version(),
        "major": flame.get_version_major(),
        "minor": flame.get_version_minor(),
        "patch": flame.get_version_patch()
    }


def get_flame_install_root():
    return "/opt/Autodesk"
