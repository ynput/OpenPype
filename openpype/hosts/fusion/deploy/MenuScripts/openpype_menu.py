import os
import sys
import openpype

from openpype.api import Logger

log = Logger().get_logger(__name__)


def main(env):
    # This script working directory starts in Fusion application folder.
    # However the contents of that folder can conflict with Qt library dlls
    # so we make sure to move out of it to avoid DLL Load Failed errors.
    os.chdir("..")

    import avalon.api
    from openpype.hosts.fusion import api
    from openpype.hosts.fusion.api import menu

    # Registers pype's Global pyblish plugins
    openpype.install()

    # activate resolve from pype
    avalon.api.install(api)

    log.info(f"Avalon registered hosts: {avalon.api.registered_host()}")

    menu.launch_openpype_menu()

    # Initiate a QTimer to check if Fusion is still alive every X interval
    # If Fusion is not found - kill itself
    # todo(roy): Implement timer that ensures UI doesn't remain when e.g.
    #            Fusion closes down


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
