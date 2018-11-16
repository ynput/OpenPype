# :coding: utf-8
# :copyright: Copyright (c) 2013 ftrack

import abc

import ftrack_api.exception


class Accessor(object):
    '''Provide data access to a location.

    A location represents a specific storage, but access to that storage may
    vary. For example, both local filesystem and FTP access may be possible for
    the same storage. An accessor implements these different ways of accessing
    the same data location.

    As different accessors may access the same location, only part of a data
    path that is commonly understood may be stored in the database. The format
    of this path should be a contract between the accessors that require access
    to the same location and is left as an implementation detail. As such, this
    system provides no guarantee that two different accessors can provide access
    to the same location, though this is a clear goal. The path stored centrally
    is referred to as the **resource identifier** and should be used when
    calling any of the accessor methods that accept a *resource_identifier*
    argument.

    '''

    __metaclass__ = abc.ABCMeta

    def __init__(self):
        '''Initialise location accessor.'''
        super(Accessor, self).__init__()

    @abc.abstractmethod
    def list(self, resource_identifier):
        '''Return list of entries in *resource_identifier* container.

        Each entry in the returned list should be a valid resource identifier.

        Raise :exc:`~ftrack_api.exception.AccessorResourceNotFoundError` if
        *resource_identifier* does not exist or
        :exc:`~ftrack_api.exception.AccessorResourceInvalidError` if
        *resource_identifier* is not a container.

        '''

    @abc.abstractmethod
    def exists(self, resource_identifier):
        '''Return if *resource_identifier* is valid and exists in location.'''

    @abc.abstractmethod
    def is_file(self, resource_identifier):
        '''Return whether *resource_identifier* refers to a file.'''

    @abc.abstractmethod
    def is_container(self, resource_identifier):
        '''Return whether *resource_identifier* refers to a container.'''

    @abc.abstractmethod
    def is_sequence(self, resource_identifier):
        '''Return whether *resource_identifier* refers to a file sequence.'''

    @abc.abstractmethod
    def open(self, resource_identifier, mode='rb'):
        '''Return :class:`~ftrack_api.data.Data` for *resource_identifier*.'''

    @abc.abstractmethod
    def remove(self, resource_identifier):
        '''Remove *resource_identifier*.

        Raise :exc:`~ftrack_api.exception.AccessorResourceNotFoundError` if
        *resource_identifier* does not exist.

        '''

    @abc.abstractmethod
    def make_container(self, resource_identifier, recursive=True):
        '''Make a container at *resource_identifier*.

        If *recursive* is True, also make any intermediate containers.

        Should silently ignore existing containers and not recreate them.

        '''

    @abc.abstractmethod
    def get_container(self, resource_identifier):
        '''Return resource_identifier of container for *resource_identifier*.

        Raise :exc:`~ftrack_api.exception.AccessorParentResourceNotFoundError`
        if container of *resource_identifier* could not be determined.

        '''

    def remove_container(self, resource_identifier):  # pragma: no cover
        '''Remove container at *resource_identifier*.'''
        return self.remove(resource_identifier)

    def get_filesystem_path(self, resource_identifier):  # pragma: no cover
        '''Return filesystem path for *resource_identifier*.

        Raise :exc:`~ftrack_api.exception.AccessorFilesystemPathError` if
        filesystem path could not be determined from *resource_identifier* or
        :exc:`~ftrack_api.exception.AccessorUnsupportedOperationError` if
        retrieving filesystem paths is not supported by this accessor.

        '''
        raise ftrack_api.exception.AccessorUnsupportedOperationError(
            'get_filesystem_path', resource_identifier=resource_identifier
        )

    def get_url(self, resource_identifier):
        '''Return URL for *resource_identifier*.

        Raise :exc:`~ftrack_api.exception.AccessorFilesystemPathError` if
        URL could not be determined from *resource_identifier* or
        :exc:`~ftrack_api.exception.AccessorUnsupportedOperationError` if
        retrieving URL is not supported by this accessor.

        '''
        raise ftrack_api.exception.AccessorUnsupportedOperationError(
            'get_url', resource_identifier=resource_identifier
        )
