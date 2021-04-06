#!/usr/bin/env python
import os
import sys
import openpype


def main(env):
    import openpype.hosts.resolve as bmdvr
    # Registers openpype's Global pyblish plugins
    openpype.install()
    bmdvr.setup(env)


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
