#! python3

"""
Resolve's tools for setting environment
"""

import sys
import os
import shutil

from pypeapp import Logger

log = Logger().get_logger(__name__, "resolve")

UTILITY_SCRIPTS = os.path.join(
    os.path.dirname(__file__),
    "resolve_utility_scripts"
)


def get_resolve_module():
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

    return bmd.scriptapp("Resolve")


def _sync_utility_scripts(env=None):
    """ Synchronizing basic utlility scripts for resolve.

    To be able to run scripts from inside `Resolve/Workspace/Scripts` menu
    all scripts has to be accessible from defined folder.
    """
    if not env:
        env = os.environ

    us_dir = env.get("RESOLVE_UTILITY_SCRIPTS_DIR", "")
    scripts = os.listdir(UTILITY_SCRIPTS)

    log.info(f"Utility Scripts Dir: `{UTILITY_SCRIPTS}`")
    log.info(f"Utility Scripts: `{scripts}`")

    # make sure no script file is in folder
    if next((s for s in os.listdir(us_dir)), None):
        for s in os.listdir(us_dir):
            path = os.path.join(us_dir, s)
            log.info(f"Removing `{path}`...")
            os.remove(path)

    # copy scripts into Resolve's utility scripts dir
    for s in scripts:
        src = os.path.join(UTILITY_SCRIPTS, s)
        dst = os.path.join(us_dir, s)
        log.info(f"Copying `{src}` to `{dst}`...")
        shutil.copy2(src, dst)


def setup(env=None):
    """ Wrapper installer started from pype.hooks.resolve.ResolvePrelaunch()
    """
    if not env:
        env = os.environ

    # synchronize resolve utility scripts
    _sync_utility_scripts(env)

    log.info("Resolve Pype wrapper has been installed")
