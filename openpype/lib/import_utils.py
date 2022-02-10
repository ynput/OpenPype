import os
import sys
import importlib
from .log import PypeLogger as Logger

log = Logger().get_logger(__name__)


def discover_host_vendor_module(module_name):
    host = os.environ["AVALON_APP"]
    pype_root = os.environ["OPENPYPE_REPOS_ROOT"]
    main_module = module_name.split(".")[0]
    module_path = os.path.join(
        pype_root, "hosts", host, "vendor", main_module)

    log.debug(
        "Importing module from host vendor path: `{}`".format(module_path))

    if not os.path.exists(module_path):
        log.warning(
            "Path not existing: `{}`".format(module_path))
        return None

    sys.path.insert(1, module_path)
    return importlib.import_module(module_name)
