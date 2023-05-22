# -*- coding: utf-8 -*-
import re

from ..utilities import ManagerBase


class OpenPypeManager(ManagerBase):
    @property
    def _reference_prefix(self):
        return "op://"

    def entityExists(self, entityRefs, context, hostSession):
        ...



    def entityName(self, entityRefs, context, hostSession):
        names = []
        for entity_ref in entityRefs:
            parsed = self.parse_reference(entity_ref)
            names.append((
                f'{parsed["project"]}/{parsed["hierarchy"]}/'
                f'{parsed["asset"]}/{parsed["subset"]}@{parsed["version"]}:'
                f'{parsed["representation"]}'
            ))
        return names

    def entityDisplayName(self, entityRefs, context, hostSession):
        names = []
        for entity_ref in entityRefs:
            parsed = self.parse_reference(entity_ref)
            names.append((
                f'{parsed["hierarchy"]}/{parsed["asset"]}'
                f' - {parsed["subset"]}@{parsed["version"]}:'
                f'{parsed["representation"]}'
            ))
        return names


    def getRelatedReferences(self, entityRefs, relationshipTraitsDatas,
                             context, hostSession, resultTraitSet=None):
        pass


    def resolve(self, entityReferences, *args, **kwargs):
        ...
