import os
import sys
import importlib
import avalon
import pype

from pypeapp import Logger

log = Logger().get_logger(__name__)


def main(env):
    # Registers pype's Global pyblish plugins
    pype.install()

    # Register Host (and it's pyblish plugins)
    host_name = env["AVALON_APP"]
    host_import_str = "pype.resolve"

    try:
        host_module = importlib.import_module(host_import_str)
    except ModuleNotFoundError:
        log.error((
            f"Host \"{host_name}\" can't be imported."
            f" Import string \"{host_import_str}\" failed."
        ))
        return False

    avalon.api.install(host_module)
    avalon.api.register_host("resolve")


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
