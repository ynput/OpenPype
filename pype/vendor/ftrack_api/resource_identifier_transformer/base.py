# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack


from builtins import object
class ResourceIdentifierTransformer(object):
    '''Transform resource identifiers.

    Provide ability to modify resource identifier before it is stored centrally
    (:meth:`encode`), or after it has been retrieved, but before it is used
    locally (:meth:`decode`).

    For example, you might want to decompose paths into a set of key, value
    pairs to store centrally and then compose a path from those values when
    reading back.

    .. note::

        This is separate from any transformations an
        :class:`ftrack_api.accessor.base.Accessor` may perform and is targeted
        towards common transformations.

    '''

    def __init__(self, session):
        '''Initialise resource identifier transformer.

        *session* should be the :class:`ftrack_api.session.Session` instance
        to use for communication with the server.

        '''
        self.session = session
        super(ResourceIdentifierTransformer, self).__init__()

    def encode(self, resource_identifier, context=None):
        '''Return encoded *resource_identifier* for storing centrally.

        A mapping of *context* values may be supplied to guide the
        transformation.

        '''
        return resource_identifier

    def decode(self, resource_identifier, context=None):
        '''Return decoded *resource_identifier* for use locally.

        A mapping of *context* values may be supplied to guide the
        transformation.

        '''
        return resource_identifier
