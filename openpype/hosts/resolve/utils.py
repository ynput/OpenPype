import os
import shutil
from openpype.lib import Logger, is_running_from_build

from openpype import AYON_SERVER_ENABLED
RESOLVE_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def setup(env):
    log = Logger.get_logger("ResolveSetup")
    scripts = {}
    util_scripts_env = env.get("RESOLVE_UTILITY_SCRIPTS_SOURCE_DIR")
    util_scripts_dir = env["RESOLVE_UTILITY_SCRIPTS_DIR"]

    util_scripts_paths = [os.path.join(
        RESOLVE_ROOT_DIR,
        "utility_scripts"
    )]

    # collect script dirs
    if util_scripts_env:
        log.info("Utility Scripts Env: `{}`".format(util_scripts_env))
        util_scripts_paths = util_scripts_env.split(
            os.pathsep) + util_scripts_paths

    # collect scripts from dirs
    for path in util_scripts_paths:
        scripts.update({path: os.listdir(path)})

    log.info("Utility Scripts Dir: `{}`".format(util_scripts_paths))
    log.info("Utility Scripts: `{}`".format(scripts))

    # Make sure scripts dir exists
    os.makedirs(util_scripts_dir, exist_ok=True)

    # make sure no script file is in folder
    for script in os.listdir(util_scripts_dir):
        path = os.path.join(util_scripts_dir, script)
        log.info("Removing `{}`...".format(path))
        if os.path.isdir(path):
            shutil.rmtree(path, onerror=None)
        else:
            os.remove(path)

    # copy scripts into Resolve's utility scripts dir
    for directory, scripts in scripts.items():
        for script in scripts:
            if (
                is_running_from_build() and
                script in ["tests", "develop"]
            ):
                # only copy those if started from build
                continue

            src = os.path.join(directory, script)
            dst = os.path.join(util_scripts_dir, script)

            # TODO: remove this once we have a proper solution
            if AYON_SERVER_ENABLED:
                if "OpenPype__Menu.py" == script:
                    continue
            else:
                if "AYON__Menu.py" == script:
                    continue

            # TODO: Make this a less hacky workaround
            if script == "openpype_startup.scriptlib":
                # Handle special case for scriptlib that needs to be a folder
                # up from the Comp folder in the Fusion scripts
                dst = os.path.join(os.path.dirname(util_scripts_dir),
                                   script)

            log.info("Copying `{}` to `{}`...".format(src, dst))
            if os.path.isdir(src):
                shutil.copytree(
                    src, dst, symlinks=False,
                    ignore=None, ignore_dangling_symlinks=False
                )
            else:
                shutil.copy2(src, dst)
