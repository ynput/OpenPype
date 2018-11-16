# :coding: utf-8
# :copyright: Copyright (c) 2013 ftrack

import os
import sys
import errno
import contextlib

import ftrack_api._python_ntpath as ntpath
import ftrack_api.accessor.base
import ftrack_api.data
from ftrack_api.exception import (
    AccessorFilesystemPathError,
    AccessorUnsupportedOperationError,
    AccessorResourceNotFoundError,
    AccessorOperationFailedError,
    AccessorPermissionDeniedError,
    AccessorResourceInvalidError,
    AccessorContainerNotEmptyError,
    AccessorParentResourceNotFoundError
)


class DiskAccessor(ftrack_api.accessor.base.Accessor):
    '''Provide disk access to a location.

    Expect resource identifiers to refer to relative filesystem paths.

    '''

    def __init__(self, prefix, **kw):
        '''Initialise location accessor.

        *prefix* specifies the base folder for the disk based structure and
        will be prepended to any path. It should be specified in the syntax of
        the current OS.

        '''
        if prefix:
            prefix = os.path.expanduser(os.path.expandvars(prefix))
            prefix = os.path.abspath(prefix)
        self.prefix = prefix

        super(DiskAccessor, self).__init__(**kw)

    def list(self, resource_identifier):
        '''Return list of entries in *resource_identifier* container.

        Each entry in the returned list should be a valid resource identifier.

        Raise :exc:`~ftrack_api.exception.AccessorResourceNotFoundError` if
        *resource_identifier* does not exist or
        :exc:`~ftrack_api.exception.AccessorResourceInvalidError` if
        *resource_identifier* is not a container.

        '''
        filesystem_path = self.get_filesystem_path(resource_identifier)

        with error_handler(
            operation='list', resource_identifier=resource_identifier
        ):
            listing = []
            for entry in os.listdir(filesystem_path):
                listing.append(os.path.join(resource_identifier, entry))

        return listing

    def exists(self, resource_identifier):
        '''Return if *resource_identifier* is valid and exists in location.'''
        filesystem_path = self.get_filesystem_path(resource_identifier)
        return os.path.exists(filesystem_path)

    def is_file(self, resource_identifier):
        '''Return whether *resource_identifier* refers to a file.'''
        filesystem_path = self.get_filesystem_path(resource_identifier)
        return os.path.isfile(filesystem_path)

    def is_container(self, resource_identifier):
        '''Return whether *resource_identifier* refers to a container.'''
        filesystem_path = self.get_filesystem_path(resource_identifier)
        return os.path.isdir(filesystem_path)

    def is_sequence(self, resource_identifier):
        '''Return whether *resource_identifier* refers to a file sequence.'''
        raise AccessorUnsupportedOperationError(operation='is_sequence')

    def open(self, resource_identifier, mode='rb'):
        '''Return :class:`~ftrack_api.Data` for *resource_identifier*.'''
        filesystem_path = self.get_filesystem_path(resource_identifier)

        with error_handler(
            operation='open', resource_identifier=resource_identifier
        ):
            data = ftrack_api.data.File(filesystem_path, mode)

        return data

    def remove(self, resource_identifier):
        '''Remove *resource_identifier*.

        Raise :exc:`~ftrack_api.exception.AccessorResourceNotFoundError` if
        *resource_identifier* does not exist.

        '''
        filesystem_path = self.get_filesystem_path(resource_identifier)

        if self.is_file(resource_identifier):
            with error_handler(
                operation='remove', resource_identifier=resource_identifier
            ):
                os.remove(filesystem_path)

        elif self.is_container(resource_identifier):
            with error_handler(
                operation='remove', resource_identifier=resource_identifier
            ):
                os.rmdir(filesystem_path)

        else:
            raise AccessorResourceNotFoundError(
                resource_identifier=resource_identifier
            )

    def make_container(self, resource_identifier, recursive=True):
        '''Make a container at *resource_identifier*.

        If *recursive* is True, also make any intermediate containers.

        '''
        filesystem_path = self.get_filesystem_path(resource_identifier)

        with error_handler(
            operation='makeContainer', resource_identifier=resource_identifier
        ):
            try:
                if recursive:
                    os.makedirs(filesystem_path)
                else:
                    try:
                        os.mkdir(filesystem_path)
                    except OSError as error:
                        if error.errno == errno.ENOENT:
                            raise AccessorParentResourceNotFoundError(
                                resource_identifier=resource_identifier
                            )
                        else:
                            raise

            except OSError, error:
                if error.errno != errno.EEXIST:
                    raise

    def get_container(self, resource_identifier):
        '''Return resource_identifier of container for *resource_identifier*.

        Raise :exc:`~ftrack_api.exception.AccessorParentResourceNotFoundError` if
        container of *resource_identifier* could not be determined.

        '''
        filesystem_path = self.get_filesystem_path(resource_identifier)

        container = os.path.dirname(filesystem_path)

        if self.prefix:
            if not container.startswith(self.prefix):
                raise AccessorParentResourceNotFoundError(
                    resource_identifier=resource_identifier,
                    message='Could not determine container for '
                            '{resource_identifier} as container falls outside '
                            'of configured prefix.'
                )

            # Convert container filesystem path into resource identifier.
            container = container[len(self.prefix):]
            if ntpath.isabs(container):
                # Ensure that resulting path is relative by stripping any
                # leftover prefixed slashes from string.
                # E.g. If prefix was '/tmp' and path was '/tmp/foo/bar' the
                # result will be 'foo/bar'.
                container = container.lstrip('\\/')

        return container

    def get_filesystem_path(self, resource_identifier):
        '''Return filesystem path for *resource_identifier*.

        For example::

            >>> accessor = DiskAccessor('my.location', '/mountpoint')
            >>> print accessor.get_filesystem_path('test.txt')
            /mountpoint/test.txt
            >>> print accessor.get_filesystem_path('/mountpoint/test.txt')
            /mountpoint/test.txt

        Raise :exc:`ftrack_api.exception.AccessorFilesystemPathError` if filesystem
        path could not be determined from *resource_identifier*.

        '''
        filesystem_path = resource_identifier
        if filesystem_path:
            filesystem_path = os.path.normpath(filesystem_path)

        if self.prefix:
            if not os.path.isabs(filesystem_path):
                filesystem_path = os.path.normpath(
                    os.path.join(self.prefix, filesystem_path)
                )

            if not filesystem_path.startswith(self.prefix):
                raise AccessorFilesystemPathError(
                    resource_identifier=resource_identifier,
                    message='Could not determine access path for '
                            'resource_identifier outside of configured prefix: '
                            '{resource_identifier}.'
                )

        return filesystem_path


@contextlib.contextmanager
def error_handler(**kw):
    '''Conform raised OSError/IOError exception to appropriate FTrack error.'''
    try:
        yield

    except (OSError, IOError) as error:
        (exception_type, exception_value, traceback) = sys.exc_info()
        kw.setdefault('error', error)

        error_code = getattr(error, 'errno')
        if not error_code:
            raise AccessorOperationFailedError(**kw), None, traceback

        if error_code == errno.ENOENT:
            raise AccessorResourceNotFoundError(**kw), None, traceback

        elif error_code == errno.EPERM:
            raise AccessorPermissionDeniedError(**kw), None, traceback

        elif error_code == errno.ENOTEMPTY:
            raise AccessorContainerNotEmptyError(**kw), None, traceback

        elif error_code in (errno.ENOTDIR, errno.EISDIR, errno.EINVAL):
            raise AccessorResourceInvalidError(**kw), None, traceback

        else:
            raise AccessorOperationFailedError(**kw), None, traceback

    except Exception:
        raise
