# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

from builtins import object
from abc import ABCMeta, abstractmethod
from future.utils import with_metaclass


class Structure(with_metaclass(ABCMeta, object)):
    '''Structure plugin interface.

    A structure plugin should compute appropriate paths for data.

    '''

    def __init__(self, prefix=''):
        '''Initialise structure.'''
        self.prefix = prefix
        self.path_separator = '/'
        super(Structure, self).__init__()

    @abstractmethod
    def get_resource_identifier(self, entity, context=None):
        '''Return a resource identifier for supplied *entity*.

        *context* can be a mapping that supplies additional information.

        '''

    def _get_sequence_expression(self, sequence):
        '''Return a sequence expression for *sequence* component.'''
        padding = sequence['padding']
        if padding:
            expression = '%0{0}d'.format(padding)
        else:
            expression = '%d'

        return expression
