#! python3

"""
Resolve's tools for setting environment
"""

import sys
import os
import shutil
from . import HOST_DIR
from openpype.api import Logger
log = Logger().get_logger(__name__)


def get_resolve_module():
    from openpype.hosts import resolve
    # dont run if already loaded
    if resolve.api.bmdvr:
        log.info(("resolve module is assigned to "
                  f"`pype.hosts.resolve.api.bmdvr`: {resolve.api.bmdvr}"))
        return resolve.api.bmdvr
    try:
        """
        The PYTHONPATH needs to be set correctly for this import
        statement to work. An alternative is to import the
        DaVinciResolveScript by specifying absolute path
        (see ExceptionHandler logic)
        """
        import DaVinciResolveScript as bmd
    except ImportError:
        if sys.platform.startswith("darwin"):
            expected_path = ("/Library/Application Support/Blackmagic Design"
                             "/DaVinci Resolve/Developer/Scripting/Modules")
        elif sys.platform.startswith("win") \
                or sys.platform.startswith("cygwin"):
            expected_path = os.path.normpath(
                os.getenv('PROGRAMDATA') + (
                    "/Blackmagic Design/DaVinci Resolve/Support/Developer"
                    "/Scripting/Modules"
                )
            )
        elif sys.platform.startswith("linux"):
            expected_path = "/opt/resolve/libs/Fusion/Modules"

        # check if the default path has it...
        print(("Unable to find module DaVinciResolveScript from "
               "$PYTHONPATH - trying default locations"))

        module_path = os.path.normpath(
            os.path.join(
                expected_path,
                "DaVinciResolveScript.py"
            )
        )

        try:
            import imp
            bmd = imp.load_source('DaVinciResolveScript', module_path)
        except ImportError:
            # No fallbacks ... report error:
            log.error(
                ("Unable to find module DaVinciResolveScript - please "
                 "ensure that the module DaVinciResolveScript is "
                 "discoverable by python")
            )
            log.error(
                ("For a default DaVinci Resolve installation, the "
                 f"module is expected to be located in: {expected_path}")
            )
            sys.exit()
    # assign global var and return
    bmdvr = bmd.scriptapp("Resolve")
    bmdvf = bmd.scriptapp("Fusion")
    resolve.api.bmdvr = bmdvr
    resolve.api.bmdvf = bmdvf
    log.info(("Assigning resolve module to "
              f"`pype.hosts.resolve.api.bmdvr`: {resolve.api.bmdvr}"))
    log.info(("Assigning resolve module to "
              f"`pype.hosts.resolve.api.bmdvf`: {resolve.api.bmdvf}"))


def _sync_utility_scripts(env=None):
    """ Synchronizing basic utlility scripts for resolve.

    To be able to run scripts from inside `Resolve/Workspace/Scripts` menu
    all scripts has to be accessible from defined folder.
    """
    if not env:
        env = os.environ

    # initiate inputs
    scripts = {}
    us_env = env.get("RESOLVE_UTILITY_SCRIPTS_SOURCE_DIR")
    us_dir = env.get("RESOLVE_UTILITY_SCRIPTS_DIR", "")
    us_paths = [os.path.join(
        HOST_DIR,
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
            path = os.path.join(us_dir, s)
            log.info(f"Removing `{path}`...")
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
            log.info(f"Copying `{src}` to `{dst}`...")
            if os.path.isdir(src):
                shutil.copytree(
                    src, dst, symlinks=False,
                    ignore=None, ignore_dangling_symlinks=False
                )
            else:
                shutil.copy2(src, dst)


def setup(env=None):
    """ Wrapper installer started from pype.hooks.resolve.ResolvePrelaunch()
    """
    if not env:
        env = os.environ

    # synchronize resolve utility scripts
    _sync_utility_scripts(env)

    log.info("Resolve OpenPype wrapper has been installed")
