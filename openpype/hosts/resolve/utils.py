import os
import shutil
from openpype.lib import Logger

RESOLVE_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def setup(env):
    log = Logger.get_logger("ResolveSetup")
    scripts = {}
    us_env = env.get("RESOLVE_UTILITY_SCRIPTS_SOURCE_DIR")
    us_dir = env.get("RESOLVE_UTILITY_SCRIPTS_DIR", "")
    us_paths = [os.path.join(
        RESOLVE_ROOT_DIR,
        "utility_scripts"
    )]

    # collect script dirs
    if us_env:
        log.info("Utility Scripts Env: `{}`".format(us_env))
        us_paths = us_env.split(
            os.pathsep) + us_paths

    # collect scripts from dirs
    for path in us_paths:
        scripts.update({path: os.listdir(path)})

    log.info("Utility Scripts Dir: `{}`".format(us_paths))
    log.info("Utility Scripts: `{}`".format(scripts))

    # make sure no script file is in folder
    for s in os.listdir(us_dir):
        path = os.path.join(us_dir, s)
        log.info("Removing `{}`...".format(path))
        if os.path.isdir(path):
            shutil.rmtree(path, onerror=None)
        else:
            os.remove(path)

    # copy scripts into Resolve's utility scripts dir
    for d, sl in scripts.items():
        # directory and scripts list
        for s in sl:
            # script in script list
            src = os.path.join(d, s)
            dst = os.path.join(us_dir, s)
            log.info("Copying `{}` to `{}`...".format(src, dst))
            if os.path.isdir(src):
                shutil.copytree(
                    src, dst, symlinks=False,
                    ignore=None, ignore_dangling_symlinks=False
                )
            else:
                shutil.copy2(src, dst)
