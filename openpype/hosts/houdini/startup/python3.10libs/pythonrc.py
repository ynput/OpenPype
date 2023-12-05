# -*- coding: utf-8 -*-
"""AYON startup script."""
from openpype.pipeline import install_host
from openpype.hosts.houdini.api import HoudiniHost
import os


def main():
    print("Installing {} ...".format(
        os.environ.get("AVALON_LABEL") or "AYON"))
    install_host(HoudiniHost())


main()
