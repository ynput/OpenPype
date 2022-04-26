#!/usr/bin/env python
import os
import sys

from openpype.pipeline import install_host


def main(env):
    import openpype.hosts.resolve as bmdvr
    # Registers openpype's Global pyblish plugins
    install_host(bmdvr)
    bmdvr.setup(env)


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
