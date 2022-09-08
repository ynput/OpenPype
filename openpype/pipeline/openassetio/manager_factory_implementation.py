# -*- coding: utf-8 -*-
"""This is implementing openassetio.hostApi.ManagerFactory.

Until hosts are implemented this serves to provide OpenPype Manager plugin.

"""
from openassetio import hostApi


class ManagerImplementationFactory(
        hostApi.ManagerImplementationFactoryInterface):

    def identifiers(self):
        return ["io.openpype.openassetio.manager"]
