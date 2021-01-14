import os
import sys
import avalon.api as avalon
import pype

from pype.api import Logger

log = Logger().get_logger(__name__)


def main(env):
    import pype.hosts.resolve as bmdvr
    # Registers pype's Global pyblish plugins
    pype.install()

    # activate resolve from pype
    avalon.install(bmdvr)

    log.info(f"Avalon registred hosts: {avalon.registered_host()}")

    bmdvr.launch_pype_menu()


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
