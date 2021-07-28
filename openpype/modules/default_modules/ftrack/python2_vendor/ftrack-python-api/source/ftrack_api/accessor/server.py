# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import os
import hashlib
import base64
import json

import requests

from .base import Accessor
from ..data import String
import ftrack_api.exception
import ftrack_api.symbol


class ServerFile(String):
    '''Representation of a server file.'''

    def __init__(self, resource_identifier, session, mode='rb'):
        '''Initialise file.'''
        self.mode = mode
        self.resource_identifier = resource_identifier
        self._session = session
        self._has_read = False

        super(ServerFile, self).__init__()

    def flush(self):
        '''Flush all changes.'''
        super(ServerFile, self).flush()

        if self.mode == 'wb':
            self._write()

    def read(self, limit=None):
        '''Read file.'''
        if not self._has_read:
            self._read()
            self._has_read = True

        return super(ServerFile, self).read(limit)

    def _read(self):
        '''Read all remote content from key into wrapped_file.'''
        position = self.tell()
        self.seek(0)

        response = requests.get(
            '{0}/component/get'.format(self._session.server_url),
            params={
                'id': self.resource_identifier,
                'username': self._session.api_user,
                'apiKey': self._session.api_key
            },
            stream=True
        )

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            raise ftrack_api.exception.AccessorOperationFailedError(
                'Failed to read data: {0}.'.format(error)
            )

        for block in response.iter_content(ftrack_api.symbol.CHUNK_SIZE):
            self.wrapped_file.write(block)

        self.flush()
        self.seek(position)

    def _write(self):
        '''Write current data to remote key.'''
        position = self.tell()
        self.seek(0)

        # Retrieve component from cache to construct a filename.
        component = self._session.get('FileComponent', self.resource_identifier)
        if not component:
            raise ftrack_api.exception.AccessorOperationFailedError(
                'Unable to retrieve component with id: {0}.'.format(
                    self.resource_identifier
                )
            )

        # Construct a name from component name and file_type.
        name = component['name']
        if component['file_type']:
            name = u'{0}.{1}'.format(
                name,
                component['file_type'].lstrip('.')
            )

        try:
            metadata = self._session.get_upload_metadata(
                component_id=self.resource_identifier,
                file_name=name,
                file_size=self._get_size(),
                checksum=self._compute_checksum()
            )
        except Exception as error:
            raise ftrack_api.exception.AccessorOperationFailedError(
                'Failed to get put metadata: {0}.'.format(error)
            )

        # Ensure at beginning of file before put.
        self.seek(0)

        # Put the file based on the metadata.
        response = requests.put(
            metadata['url'],
            data=self.wrapped_file,
            headers=metadata['headers']
        )

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            raise ftrack_api.exception.AccessorOperationFailedError(
                'Failed to put file to server: {0}.'.format(error)
            )

        self.seek(position)

    def _get_size(self):
        '''Return size of file in bytes.'''
        position = self.tell()
        self.seek(0, os.SEEK_END)
        length = self.tell()
        self.seek(position)
        return length

    def _compute_checksum(self):
        '''Return checksum for file.'''
        fp = self.wrapped_file
        buf_size = ftrack_api.symbol.CHUNK_SIZE
        hash_obj = hashlib.md5()
        spos = fp.tell()

        s = fp.read(buf_size)
        while s:
            hash_obj.update(s)
            s = fp.read(buf_size)

        base64_digest = base64.encodestring(hash_obj.digest())
        if base64_digest[-1] == '\n':
            base64_digest = base64_digest[0:-1]

        fp.seek(spos)
        return base64_digest


class _ServerAccessor(Accessor):
    '''Provide server location access.'''

    def __init__(self, session, **kw):
        '''Initialise location accessor.'''
        super(_ServerAccessor, self).__init__(**kw)

        self._session = session

    def open(self, resource_identifier, mode='rb'):
        '''Return :py:class:`~ftrack_api.Data` for *resource_identifier*.'''
        return ServerFile(resource_identifier, session=self._session, mode=mode)

    def remove(self, resourceIdentifier):
        '''Remove *resourceIdentifier*.'''
        response = requests.get(
            '{0}/component/remove'.format(self._session.server_url),
            params={
                'id': resourceIdentifier,
                'username': self._session.api_user,
                'apiKey': self._session.api_key
            }
        )
        if response.status_code != 200:
            raise ftrack_api.exception.AccessorOperationFailedError(
                'Failed to remove file.'
            )

    def get_container(self, resource_identifier):
        '''Return resource_identifier of container for *resource_identifier*.'''
        return None

    def make_container(self, resource_identifier, recursive=True):
        '''Make a container at *resource_identifier*.'''

    def list(self, resource_identifier):
        '''Return list of entries in *resource_identifier* container.'''
        raise NotImplementedError()

    def exists(self, resource_identifier):
        '''Return if *resource_identifier* is valid and exists in location.'''
        return False

    def is_file(self, resource_identifier):
        '''Return whether *resource_identifier* refers to a file.'''
        raise NotImplementedError()

    def is_container(self, resource_identifier):
        '''Return whether *resource_identifier* refers to a container.'''
        raise NotImplementedError()

    def is_sequence(self, resource_identifier):
        '''Return whether *resource_identifier* refers to a file sequence.'''
        raise NotImplementedError()

    def get_url(self, resource_identifier):
        '''Return url for *resource_identifier*.'''
        url_string = (
            u'{url}/component/get?id={id}&username={username}'
            u'&apiKey={apiKey}'
        )
        return url_string.format(
            url=self._session.server_url,
            id=resource_identifier,
            username=self._session.api_user,
            apiKey=self._session.api_key
        )

    def get_thumbnail_url(self, resource_identifier, size=None):
        '''Return thumbnail url for *resource_identifier*.

        Optionally, specify *size* to constrain the downscaled image to size
        x size pixels.
        '''
        url_string = (
            u'{url}/component/thumbnail?id={id}&username={username}'
            u'&apiKey={apiKey}'
        )
        url = url_string.format(
            url=self._session.server_url,
            id=resource_identifier,
            username=self._session.api_user,
            apiKey=self._session.api_key
        )
        if size:
            url += u'&size={0}'.format(size)

        return url
