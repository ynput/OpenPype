# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import os
import tempfile

import pytest

import ftrack_api.data


@pytest.fixture()
def content():
    '''Return initial content.'''
    return 'test data'


@pytest.fixture(params=['file', 'file_wrapper', 'string'])
def data(request, content):
    '''Return cache.'''

    if request.param == 'string':
        data_object = ftrack_api.data.String(content)

    elif request.param == 'file':
        file_handle, path = tempfile.mkstemp()
        file_object = os.fdopen(file_handle, 'r+')
        file_object.write(content)
        file_object.flush()
        file_object.close()

        data_object = ftrack_api.data.File(path, 'r+')

        def cleanup():
            '''Cleanup.'''
            data_object.close()
            os.remove(path)

        request.addfinalizer(cleanup)

    elif request.param == 'file_wrapper':
        file_handle, path = tempfile.mkstemp()
        file_object = os.fdopen(file_handle, 'r+')
        file_object.write(content)
        file_object.seek(0)

        data_object = ftrack_api.data.FileWrapper(file_object)

        def cleanup():
            '''Cleanup.'''
            data_object.close()
            os.remove(path)

        request.addfinalizer(cleanup)

    else:
        raise ValueError('Unrecognised parameter: {0}'.format(request.param))

    return data_object


def test_read(data, content):
    '''Return content from current position up to *limit*.'''
    assert data.read(5) == content[:5]
    assert data.read() == content[5:]


def test_write(data, content):
    '''Write content at current position.'''
    assert data.read() == content
    data.write('more test data')
    data.seek(0)
    assert data.read() == content + 'more test data'


def test_flush(data):
    '''Flush buffers ensuring data written.'''
    # TODO: Implement better test than just calling function.
    data.flush()


def test_seek(data, content):
    '''Move internal pointer to *position*.'''
    data.seek(5)
    assert data.read() == content[5:]


def test_tell(data):
    '''Return current position of internal pointer.'''
    assert data.tell() == 0
    data.seek(5)
    assert data.tell() == 5


def test_close(data):
    '''Flush buffers and prevent further access.'''
    data.close()
    with pytest.raises(ValueError) as error:
        data.read()

    assert 'I/O operation on closed file' in str(error.value)


class Dummy(ftrack_api.data.Data):
    '''Dummy string.'''

    def read(self, limit=None):
        '''Return content from current position up to *limit*.'''

    def write(self, content):
        '''Write content at current position.'''


def test_unsupported_tell():
    '''Fail when tell unsupported.'''
    data = Dummy()
    with pytest.raises(NotImplementedError) as error:
        data.tell()

    assert 'Tell not supported' in str(error.value)


def test_unsupported_seek():
    '''Fail when seek unsupported.'''
    data = Dummy()
    with pytest.raises(NotImplementedError) as error:
        data.seek(5)

    assert 'Seek not supported' in str(error.value)
