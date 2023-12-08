# -*- coding: utf-8 -*-
"""OpenPype startup script."""
from openpype.pipeline import install_host
from openpype.hosts.houdini.api import HoudiniHost
from openpype import AYON_SERVER_ENABLED


def main():
    print("Installing {} ...".format(
        "AYON" if AYON_SERVER_ENABLED else "OpenPype"))
    install_host(HoudiniHost())


main()
