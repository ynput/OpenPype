# -*- coding: utf-8 -*-
from openassetio import hostApi, constants, TraitsData
from openassetio.managerApi import ManagerInterface

__all__ = ['OpenPypeManager']


class OpenPypeManager(ManagerInterface):

    def entityExists(self, entityRefs, context, hostSession):
        pass

    def entityName(self, entityRefs, context, hostSession):
        pass

    def entityDisplayName(self, entityRefs, context, hostSession):
        pass

    def getRelatedReferences(self, entityRefs, relationshipTraitsDatas, context, hostSession, resultTraitSet=None):
        pass

    def managementPolicy(self, traitSet, Set=None, p_str=None, *args, **kwargs):
        return [TraitsData() for _ in traitSet]

    def identifier(self):
        return "io.openpype.openassetio.manager"

    def displayName(self):
        return "OpenPype Manager"

    def info(self):
        ...
