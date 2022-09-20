import os
import sys

from openpype.lib import Logger
from openpype.pipeline import (
    install_host,
    registered_host,
)


def main(env):
    # This script working directory starts in Fusion application folder.
    # However the contents of that folder can conflict with Qt library dlls
    # so we make sure to move out of it to avoid DLL Load Failed errors.
    os.chdir("..")
    from openpype.hosts.fusion.api import FusionHost
    from openpype.hosts.fusion.api import menu

    # activate resolve from pype
    install_host(FusionHost())

    log = Logger.get_logger(__name__)
    log.info(f"Registered host: {registered_host()}")

    menu.launch_openpype_menu()

    # Initiate a QTimer to check if Fusion is still alive every X interval
    # If Fusion is not found - kill itself
    # todo(roy): Implement timer that ensures UI doesn't remain when e.g.
    #            Fusion closes down


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
