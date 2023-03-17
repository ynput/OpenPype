# -*- coding: utf-8 -*-
"""OpenPype startup script."""
from openpype.pipeline import install_host
from openpype.hosts.houdini.api import HoudiniHost


def main():
    print("Installing OpenPype ...")
    install_host(HoudiniHost())


main()
