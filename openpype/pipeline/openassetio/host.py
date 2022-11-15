# -*- coding: utf-8 -*-
from openassetio.hostApi import HostInterface


class ExampleHost(HostInterface):
    """A minimal host implementation."""
    def identifier(self):
        return "io.openpype.host"

    def displayName(self):
        return "OpenPype OpenAssetIO Host"
