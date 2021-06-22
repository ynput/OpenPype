import os
import sys
import importlib
from .log import PypeLogger as Logger
from pathlib import Path

log = Logger().get_logger(__name__)


def discover_host_vendor_module(module_name):
    host = os.environ["AVALON_APP"]
    pype_root = os.environ["OPENPYPE_REPOS_ROOT"]
    main_module = module_name.split(".")[0]
    module_path = os.path.join(
        pype_root, "hosts", host, "vendor", main_module)

    log.debug(
        "Importing moduel from host vendor path: `{}`".format(module_path))

    if not os.path.exists(module_path):
        log.warning(
            "Path not existing: `{}`".format(module_path))
        return None

    sys.path.insert(1, module_path)
    return importlib.import_module(module_name)


def get_pyside2_location():
    """Get location of PySide2 and its dependencies.

    Returned path can be used with `site.addsitedir()`

    Returns:
        str: path to PySide2

    """
    path = Path(os.getenv("OPENPYPE_ROOT"))
    path = path / "vendor/python/PySide2"
    return str(path)
