# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import os
import tempfile

import pytest

import ftrack_api
import ftrack_api.exception
import ftrack_api.accessor.disk
import ftrack_api.data


def test_get_filesystem_path(temporary_path):
    '''Convert paths to filesystem paths.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)

    # Absolute paths outside of configured prefix fail.
    with pytest.raises(ftrack_api.exception.AccessorFilesystemPathError):
        accessor.get_filesystem_path(os.path.join('/', 'test', 'foo.txt'))

    # Absolute root path.
    assert accessor.get_filesystem_path(temporary_path) == temporary_path

    # Absolute path within prefix.
    assert (
        accessor.get_filesystem_path(
            os.path.join(temporary_path, 'test.txt')
        ) ==
        os.path.join(temporary_path, 'test.txt')
    )

    # Relative root path
    assert accessor.get_filesystem_path('') == temporary_path

    # Relative path for file at root
    assert (accessor.get_filesystem_path('test.txt') ==
            os.path.join(temporary_path, 'test.txt'))

    # Relative path for file in subdirectory
    assert (accessor.get_filesystem_path('test/foo.txt') ==
            os.path.join(temporary_path, 'test', 'foo.txt'))

    # Relative path non-collapsed
    assert (accessor.get_filesystem_path('test/../foo.txt') ==
            os.path.join(temporary_path, 'foo.txt'))

    # Relative directory path without trailing slash
    assert (accessor.get_filesystem_path('test') ==
            os.path.join(temporary_path, 'test'))

    # Relative directory path with trailing slash
    assert (accessor.get_filesystem_path('test/') ==
            os.path.join(temporary_path, 'test'))


def test_list(temporary_path):
    '''List entries.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)

    # File in root directory
    assert accessor.list('') == []
    data = accessor.open('test.txt', 'w+')
    data.close()
    assert accessor.list('') == ['test.txt']

    # File in subdirectory
    accessor.make_container('test_dir')
    assert accessor.list('test_dir') == []
    data = accessor.open('test_dir/test.txt', 'w+')
    data.close()

    listing = accessor.list('test_dir')
    assert listing == [os.path.join('test_dir', 'test.txt')]

    # Is a valid resource
    assert accessor.exists(listing[0]) is True


def test_exists(temporary_path):
    '''Valid path exists.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)

    _, temporary_file = tempfile.mkstemp(dir=temporary_path)
    assert accessor.exists(temporary_file) is True


def test_missing_does_not_exist(temporary_path):
    '''Missing path does not exist.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)
    assert accessor.exists('non-existant.txt') is False


def test_is_file(temporary_path):
    '''Valid file is considered a file.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)

    _, temporary_file = tempfile.mkstemp(dir=temporary_path)
    assert accessor.is_file(temporary_file) is True


def test_missing_is_not_file(temporary_path):
    '''Missing path is not considered a file.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)
    assert accessor.is_file('non_existant.txt') is False


def test_container_is_not_file(temporary_path):
    '''Valid container is not considered a file.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)

    temporary_directory = tempfile.mkdtemp(dir=temporary_path)
    assert accessor.is_file(temporary_directory) is False


def test_is_container(temporary_path):
    '''Valid container is considered a container.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)

    temporary_directory = tempfile.mkdtemp(dir=temporary_path)
    assert accessor.is_container(temporary_directory) is True


def test_missing_is_not_container(temporary_path):
    '''Missing path is not considered a container.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)
    assert accessor.is_container('non_existant') is False


def test_file_is_not_container(temporary_path):
    '''Valid file is not considered a container.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)

    _, temporary_file = tempfile.mkstemp(dir=temporary_path)
    assert accessor.is_container(temporary_file) is False


def test_is_sequence(temporary_path):
    '''Sequence detection unsupported.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)

    with pytest.raises(
        ftrack_api.exception.AccessorUnsupportedOperationError
    ):
        accessor.is_sequence('foo.%04d.exr')


def test_open(temporary_path):
    '''Open file.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)

    with pytest.raises(ftrack_api.exception.AccessorResourceNotFoundError):
        accessor.open('test.txt', 'r')

    data = accessor.open('test.txt', 'w+')
    assert isinstance(data, ftrack_api.data.Data) is True
    assert data.read() == ''
    data.write('test data')
    data.close()

    data = accessor.open('test.txt', 'r')
    assert (data.read() == 'test data')
    data.close()


def test_remove_file(temporary_path):
    '''Delete file at path.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)

    file_handle, temporary_file = tempfile.mkstemp(dir=temporary_path)
    os.close(file_handle)
    accessor.remove(temporary_file)
    assert os.path.exists(temporary_file) is False


def test_remove_container(temporary_path):
    '''Delete container at path.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)

    temporary_directory = tempfile.mkdtemp(dir=temporary_path)
    accessor.remove(temporary_directory)
    assert os.path.exists(temporary_directory) is False


def test_remove_missing(temporary_path):
    '''Fail to remove path that does not exist.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)
    with pytest.raises(ftrack_api.exception.AccessorResourceNotFoundError):
        accessor.remove('non_existant')


def test_make_container(temporary_path):
    '''Create container.'''
    accessor = ftrack_api.accessor.disk.DiskAccessor(temporary_path)

    accessor.make_container('test')
    assert os.path.isdir(os.path.join(temporary_path, 'test')) is True

    # Recursive
    accessor.make_container('test/a/b/c')
    assert (
        os.path.isdir(
            os.path.join(temporary_path, 'test', 'a', 'b', 'c')
        ) is
        True
    )

    # Non-recursive fail
    with pytest.raises(
        ftrack_api.exception.AccessorParentResourceNotFoundError
    ):
        accessor.make_container('test/d/e/f', recursive=False)

    # Existing succeeds
    accessor.make_container('test/a/b/c')


def test_get_container(temporary_path):
    '''Get container from resource_identifier.'''
    # With prefix.
    accessor = ftrack_api.accessor.disk.DiskAccessor(prefix=temporary_path)

    assert (
        accessor.get_container(os.path.join('test', 'a')) ==
        'test'
    )

    assert (
        accessor.get_container(os.path.join('test', 'a/')) ==
        'test'
    )

    assert (
        accessor.get_container('test') ==
        ''
    )

    with pytest.raises(
        ftrack_api.exception.AccessorParentResourceNotFoundError
    ):
        accessor.get_container('')

    with pytest.raises(
        ftrack_api.exception.AccessorParentResourceNotFoundError
    ):
        accessor.get_container(temporary_path)

    # Without prefix.
    accessor = ftrack_api.accessor.disk.DiskAccessor(prefix='')

    assert (
        accessor.get_container(os.path.join(temporary_path, 'test', 'a')) ==
        os.path.join(temporary_path, 'test')
    )

    assert (
        accessor.get_container(
            os.path.join(temporary_path, 'test', 'a/')
        ) ==
        os.path.join(temporary_path, 'test')
    )

    assert (
        accessor.get_container(os.path.join(temporary_path, 'test')) ==
        temporary_path
    )
