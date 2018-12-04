# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import ftrack_api_old.structure.base


class EntityIdStructure(ftrack_api_old.structure.base.Structure):
    '''Entity id pass-through structure.'''

    def get_resource_identifier(self, entity, context=None):
        '''Return a *resourceIdentifier* for supplied *entity*.'''
        return entity['id']
