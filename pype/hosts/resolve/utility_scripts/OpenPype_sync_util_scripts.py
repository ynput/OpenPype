#!/usr/bin/env python
import os
import sys
import pype


def main(env):
    import pype.hosts.resolve as bmdvr
    # Registers openpype's Global pyblish plugins
    pype.install()
    bmdvr.setup(env)


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
