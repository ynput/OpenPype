import os
import sys
import avalon.api as avalon
import openpype

from openpype.api import Logger

log = Logger().get_logger(__name__)


def main(env):
    import openpype.hosts.resolve as bmdvr
    # Registers openpype's Global pyblish plugins
    openpype.install()

    # activate resolve from openpype
    avalon.install(bmdvr)

    log.info(f"Avalon registered hosts: {avalon.registered_host()}")

    bmdvr.launch_pype_menu()


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
