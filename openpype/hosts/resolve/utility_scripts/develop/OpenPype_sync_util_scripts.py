#!/usr/bin/env python
import os
import sys

from openpype.pipeline import install_host


def main(env):
    from openpype.hosts.resolve.utils import setup
    import openpype.hosts.resolve.api as bmdvr
    # Registers openpype's Global pyblish plugins
    install_host(bmdvr)
    setup(env)


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
