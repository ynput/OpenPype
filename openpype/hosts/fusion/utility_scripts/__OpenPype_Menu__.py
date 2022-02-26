import os
import sys
import openpype

from openpype.api import Logger

log = Logger().get_logger(__name__)


def main(env):
    import avalon.api
    from openpype.hosts.fusion import api
    from openpype.hosts.fusion.api import menu

    # Registers pype's Global pyblish plugins
    openpype.install()

    # activate resolve from pype
    avalon.api.install(api)

    log.info(f"Avalon registered hosts: {avalon.api.registered_host()}")

    menu.launch_openpype_menu()


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
