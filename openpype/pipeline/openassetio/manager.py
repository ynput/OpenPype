# -*- coding: utf-8 -*-
from openassetio import hostApi, constants, TraitsData
from openassetio.managerApi import ManagerInterface

__all__ = ['OpenPypeManager']


class OpenPypeManager(ManagerInterface):
    __reference_prefix = "op:///"
    __settings = {}


    def __init__(self):
        super().__init__()
        self.__settings = {}  # TODO: initialize with Settings

    def settings(self, hostSession):
        return self.__settings.copy()


    def entityExists(self, entityRefs, context, hostSession):
        pass

    def entityName(self, entityRefs, context, hostSession):
        pass

    def entityDisplayName(self, entityRefs, context, hostSession):
        pass

    def getRelatedReferences(
            self, entityRefs, relationshipTraitsDatas,
            context, hostSession, resultTraitSet=None):
        pass

    def managementPolicy(
            self, traitSet, Set=None, p_str=None, *args, **kwargs):
        return [TraitsData() for _ in traitSet]

    def identifier(self):
        return "io.openpype.openassetio.manager"

    def displayName(self):
        return "OpenPype Manager"

    def info(self):
        return {
            constants.kField_EntityReferencesMatchPrefix: self.__reference_prefix  # noqa: E501
        }

    def isEntityReferenceString(self, someString, hostSession):
        return someString.startswith(self.__reference_prefix)
