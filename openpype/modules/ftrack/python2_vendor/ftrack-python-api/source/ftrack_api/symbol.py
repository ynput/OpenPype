# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

import os


class Symbol(object):
    '''A constant symbol.'''

    def __init__(self, name, value=True):
        '''Initialise symbol with unique *name* and *value*.

        *value* is used for nonzero testing.

        '''
        self.name = name
        self.value = value

    def __str__(self):
        '''Return string representation.'''
        return self.name

    def __repr__(self):
        '''Return representation.'''
        return '{0}({1})'.format(self.__class__.__name__, self.name)

    def __nonzero__(self):
        '''Return whether symbol represents non-zero value.'''
        return bool(self.value)

    def __copy__(self):
        '''Return shallow copy.

        Overridden to always return same instance.

        '''
        return self


#: Symbol representing that no value has been set or loaded.
NOT_SET = Symbol('NOT_SET', False)

#: Symbol representing created state.
CREATED = Symbol('CREATED')

#: Symbol representing modified state.
MODIFIED = Symbol('MODIFIED')

#: Symbol representing deleted state.
DELETED = Symbol('DELETED')

#: Topic published when component added to a location.
COMPONENT_ADDED_TO_LOCATION_TOPIC = 'ftrack.location.component-added'

#: Topic published when component removed from a location.
COMPONENT_REMOVED_FROM_LOCATION_TOPIC = 'ftrack.location.component-removed'

#: Identifier of builtin origin location.
ORIGIN_LOCATION_ID = 'ce9b348f-8809-11e3-821c-20c9d081909b'

#: Identifier of builtin unmanaged location.
UNMANAGED_LOCATION_ID = 'cb268ecc-8809-11e3-a7e2-20c9d081909b'

#: Identifier of builtin review location.
REVIEW_LOCATION_ID = 'cd41be70-8809-11e3-b98a-20c9d081909b'

#: Identifier of builtin connect location.
CONNECT_LOCATION_ID = '07b82a97-8cf9-11e3-9383-20c9d081909b'

#: Identifier of builtin server location.
SERVER_LOCATION_ID = '3a372bde-05bc-11e4-8908-20c9d081909b'

#: Chunk size used when working with data, default to 1Mb.
CHUNK_SIZE = int(os.getenv('FTRACK_API_FILE_CHUNK_SIZE', 0)) or 1024*1024

#: Symbol representing syncing users with ldap
JOB_SYNC_USERS_LDAP = Symbol('SYNC_USERS_LDAP')
