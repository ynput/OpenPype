# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import pytest

import ftrack_api.structure.base


class Concrete(ftrack_api.structure.base.Structure):
    '''Concrete implementation to allow testing non-abstract methods.'''

    def get_resource_identifier(self, entity, context=None):
        '''Return a resource identifier for supplied *entity*.

        *context* can be a mapping that supplies additional information.

        '''
        return 'resource_identifier'


@pytest.mark.parametrize('sequence, expected', [
    ({'padding': None}, '%d'),
    ({'padding': 4}, '%04d')
], ids=[
    'no padding',
    'padded'
])
def test_get_sequence_expression(sequence, expected):
    '''Get sequence expression from sequence.'''
    structure = Concrete()
    assert structure._get_sequence_expression(sequence) == expected
