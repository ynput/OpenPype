#! python3

"""
Resolve's tools for setting environment
"""

import os
import sys

from openpype.lib import Logger

log = Logger.get_logger(__name__)


def get_resolve_module():
    from openpype.hosts.resolve import api
    # dont run if already loaded
    if api.bmdvr:
        log.info(("resolve module is assigned to "
                  f"`openpype.hosts.resolve.api.bmdvr`: {api.bmdvr}"))
        return api.bmdvr
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
        else:
            raise NotImplementedError(
                "Unsupported platform: {}".format(sys.platform)
            )

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
    api.bmdvr = bmdvr
    api.bmdvf = bmdvf
    log.info(("Assigning resolve module to "
              f"`openpype.hosts.resolve.api.bmdvr`: {api.bmdvr}"))
    log.info(("Assigning resolve module to "
              f"`openpype.hosts.resolve.api.bmdvf`: {api.bmdvf}"))
