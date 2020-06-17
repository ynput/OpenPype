#! python3
import sys
from pype.api import Logger

log = Logger().get_logger(__name__)


def main():
    import pype.hosts.resolve as bmdvr
    bm = bmdvr.utils.get_resolve_module()
    log.info(f"blackmagicmodule: {bm}")

import DaVinciResolveScript as bmd
print(f"_>> bmd.scriptapp(Resolve): {bmd.scriptapp('Resolve')}")


if __name__ == "__main__":
    result = main()
    sys.exit(not bool(result))
