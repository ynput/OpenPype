import os
import sys

from openpype.lib import Logger
from openpype.pipeline import (
    install_host,
    registered_host,
)


def main(env):
    from openpype.hosts.fusion import api
    from openpype.hosts.fusion.api import menu

    # activate resolve from pype
    install_host(api)

    log = Logger.get_logger(__name__)
    log.info(f"Registered host: {registered_host()}")

    menu.launch_openpype_menu()


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
