# :coding: utf-8
# :copyright: Copyright (c) 2013 ftrack

from builtins import object
import os
from abc import ABCMeta, abstractmethod
import tempfile
from future.utils import with_metaclass


class Data(with_metaclass(ABCMeta, object)):
    '''File-like object for manipulating data.'''

    def __init__(self):
        '''Initialise data access.'''
        self.closed = False

    @abstractmethod
    def read(self, limit=None):
        '''Return content from current position up to *limit*.'''

    @abstractmethod
    def write(self, content):
        '''Write content at current position.'''

    def flush(self):
        '''Flush buffers ensuring data written.'''

    def seek(self, offset, whence=os.SEEK_SET):
        '''Move internal pointer by *offset*.

        The *whence* argument is optional and defaults to os.SEEK_SET or 0
        (absolute file positioning); other values are os.SEEK_CUR or 1
        (seek relative to the current position) and os.SEEK_END or 2
        (seek relative to the file's end).

        '''
        raise NotImplementedError('Seek not supported.')

    def tell(self):
        '''Return current position of internal pointer.'''
        raise NotImplementedError('Tell not supported.')

    def close(self):
        '''Flush buffers and prevent further access.'''
        self.flush()
        self.closed = True


class FileWrapper(Data):
    '''Data wrapper for Python file objects.'''

    def __init__(self, wrapped_file):
        '''Initialise access to *wrapped_file*.'''
        self.wrapped_file = wrapped_file
        self._read_since_last_write = False
        super(FileWrapper, self).__init__()

    def read(self, limit=None):
        '''Return content from current position up to *limit*.'''
        self._read_since_last_write = True

        if limit is None:
            limit = -1

        return self.wrapped_file.read(limit)

    def write(self, content):
        '''Write content at current position.'''
        if self._read_since_last_write:
            # Windows requires a seek before switching from read to write.
            self.seek(self.tell())

        self.wrapped_file.write(content)
        self._read_since_last_write = False

    def flush(self):
        '''Flush buffers ensuring data written.'''
        super(FileWrapper, self).flush()
        if hasattr(self.wrapped_file, 'flush'):
            self.wrapped_file.flush()

    def seek(self, offset, whence=os.SEEK_SET):
        '''Move internal pointer by *offset*.'''
        self.wrapped_file.seek(offset, whence)

    def tell(self):
        '''Return current position of internal pointer.'''
        return self.wrapped_file.tell()

    def close(self):
        '''Flush buffers and prevent further access.'''
        if not self.closed:
            super(FileWrapper, self).close()
            if hasattr(self.wrapped_file, 'close'):
                self.wrapped_file.close()


class File(FileWrapper):
    '''Data wrapper accepting filepath.'''

    def __init__(self, path, mode='rb'):
        '''Open file at *path* with *mode*.'''
        file_object = open(path, mode)
        super(File, self).__init__(file_object)


class String(FileWrapper):
    '''Data wrapper using TemporaryFile instance.'''

    def __init__(self, content=None):
        '''Initialise data with *content*.'''

        # Track if data is binary or not. If it is binary then read should also
        # return binary.
        self.is_binary = True

        super(String, self).__init__(
            tempfile.TemporaryFile()
        )

        if content is not None:
            if not isinstance(content, bytes):
                self.is_binary = False
                content = content.encode()

            self.wrapped_file.write(content)
            self.wrapped_file.seek(0)

    def write(self, content):
        if not isinstance(content, bytes):
            self.is_binary = False
            content = content.encode()

        super(String, self).write(
            content
        )

    def read(self, limit=None):
        content = super(String, self).read(limit)

        if not self.is_binary:
            content = content.decode('utf-8')

        return content
