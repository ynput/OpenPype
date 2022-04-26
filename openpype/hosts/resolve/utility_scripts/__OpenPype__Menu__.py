import os
import sys

from openpype.pipeline import install_host
from openpype.api import Logger

log = Logger().get_logger(__name__)


def main(env):
    import openpype.hosts.resolve as bmdvr

    # activate resolve from openpype
    install_host(bmdvr)

    bmdvr.launch_pype_menu()


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
