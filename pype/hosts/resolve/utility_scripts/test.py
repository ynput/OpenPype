#! python3
import sys
from pype.api import Logger
import DaVinciResolveScript as bmdvr


log = Logger().get_logger(__name__)


def main():
    import pype.hosts.resolve as bmdvr
    bm = bmdvr.utils.get_resolve_module()
    log.info(f"blackmagicmodule: {bm}")


print(f"_>> bmdvr.scriptapp(Resolve): {bmdvr.scriptapp('Resolve')}")


if __name__ == "__main__":
    result = main()
    sys.exit(not bool(result))
