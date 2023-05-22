# -*- coding: utf-8 -*-
"""Definition of managers"""
from abc import ABC, abstractmethod
from openassetio import constants, TraitsData
from openassetio.managerApi import ManagerInterface


class ManagerBase(ABC, ManagerInterface):
    @property
    @abstractmethod
    def _reference_prefix(self):
        return "ayon://"

    def managementPolicy(
            self, traitSets, Set=None, p_str=None, *args, **kwargs):
        return [TraitsData() for _ in traitSets]

    def info(self):
        return {
            constants.kField_EntityReferencesMatchPrefix: self.__reference_prefix  # noqa: E501
        }

    def isEntityReferenceString(self, someString, hostSession):
        return someString.startswith(self.__reference_prefix)



class OpenPypeManager(ManagerBase):
    @property
    def _reference_prefix(self):
        return "op://"

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

    def identifier(self):
        return "io.openpype.openassetio.manager"

    def displayName(self):
        return "OpenPype Manager"
