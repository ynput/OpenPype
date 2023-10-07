import os
import sys

from openpype.pipeline import install_host
from openpype.lib import Logger

log = Logger.get_logger(__name__)


def main(env):
    from openpype.hosts.resolve.api import ResolveHost, launch_pype_menu

    # activate resolve from openpype
    host = ResolveHost()
    install_host(host)

    launch_pype_menu()


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
