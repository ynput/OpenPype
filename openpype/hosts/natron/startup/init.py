# -*- coding: utf-8 -*-
"""OpenPype startup script for Natron."""
from openpype.pipeline import install_host
from openpype.hosts.natron.api import NatronHost


def _install_openpype():
    print("Installing OpenPype ...")
    install_host(NatronHost())


_install_openpype()
