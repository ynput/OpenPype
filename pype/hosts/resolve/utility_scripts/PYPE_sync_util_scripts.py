#!/usr/bin/env python
import os
import sys
import pype
import pype.hosts.resolve as bmdvr


def main(env):
    # Registers pype's Global pyblish plugins
    pype.install()
    bmdvr.setup(env)


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
