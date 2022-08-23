# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import uuid

import pytest

import ftrack_api
import ftrack_api.exception
import ftrack_api.accessor.server
import ftrack_api.data


def test_read_and_write(new_component, session):
    '''Read and write data from server accessor.'''
    random_data = uuid.uuid1().hex

    accessor = ftrack_api.accessor.server._ServerAccessor(session)
    http_file = accessor.open(new_component['id'], mode='wb')
    http_file.write(random_data)
    http_file.close()

    data = accessor.open(new_component['id'], 'r')
    assert data.read() == random_data, 'Read data is the same as written.'
    data.close()


def test_remove_data(new_component, session):
    '''Remove data using server accessor.'''
    random_data = uuid.uuid1().hex

    accessor = ftrack_api.accessor.server._ServerAccessor(session)
    http_file = accessor.open(new_component['id'], mode='wb')
    http_file.write(random_data)
    http_file.close()

    accessor.remove(new_component['id'])

    data = accessor.open(new_component['id'], 'r')
    with pytest.raises(ftrack_api.exception.AccessorOperationFailedError):
        data.read()
