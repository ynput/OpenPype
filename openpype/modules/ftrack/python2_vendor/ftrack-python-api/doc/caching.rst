..
    :copyright: Copyright (c) 2015 ftrack


.. _caching:

*******
Caching
*******

The API makes use of caching in order to provide more efficient retrieval of
data by reducing the number of calls to the remote server::

    # First call to retrieve user performs a request to the server.
    user = session.get('User', 'some-user-id')

    # A later call in the same session to retrieve the same user just gets
    # the existing instance from the cache without a request to the server.
    user = session.get('User', 'some-user-id')

It also seamlessly merges related data together regardless of how it was
retrieved::

    >>> timelog = user['timelogs'][0]
    >>> with session.auto_populating(False):
    >>>     print timelog['comment']
    NOT_SET
    >>> session.query(
    ...     'select comment from Timelog where id is "{0}"'
    ...     .format(timelog['id'])
    ... ).all()
    >>> with session.auto_populating(False):
    >>>     print timelog['comment']
    'Some comment'

By default, each :class:`~ftrack_api.session.Session` is configured with a
simple :class:`~ftrack_api.cache.MemoryCache()` and the cache is lost as soon as
the session expires.

Configuring a session cache
===========================

It is possible to configure the cache that a session uses. An example would be a
persistent auto-populated cache that survives between sessions::

    import os
    import ftrack_api.cache

    # Specify where the file based cache should be stored.
    cache_path = os.path.join(tempfile.gettempdir(), 'ftrack_session_cache.dbm')


    # Define a cache maker that returns a file based cache. Note that a
    # function is used because the file based cache should use the session's
    # encode and decode methods to serialise the entity data to a format that
    # can be written to disk (JSON).
    def cache_maker(session):
        '''Return cache to use for *session*.'''
        return ftrack_api.cache.SerialisedCache(
            ftrack_api.cache.FileCache(cache_path),
            encode=session.encode,
            decode=session.decode
        )

    # Create the session using the cache maker.
    session = ftrack_api.Session(cache=cache_maker)

.. note::

    There can be a performance penalty when using a more complex cache setup.
    For example, serialising data and also writing and reading from disk can be
    relatively slow operations.

Regardless of the cache specified, the session will always construct a
:class:`~ftrack_api.cache.LayeredCache` with a
:class:`~ftrack_api.cache.MemoryCache` at the top level and then your cache at
the second level. This is to ensure consistency of instances returned by the
session.

You can check (or even modify) at any time what cache configuration a session is
using by accessing the `cache` attribute on a
:class:`~ftrack_api.session.Session`::

    >>> print session.cache
    <ftrack_api.cache.LayeredCache object at 0x0000000002F64400>

Writing a new cache interface
=============================

If you have a custom cache backend you should be able to integrate it into the
system by writing a cache interface that matches the one defined by
:class:`ftrack_api.cache.Cache`. This typically involves a subclass and
overriding the :meth:`~ftrack_api.cache.Cache.get`,
:meth:`~ftrack_api.cache.Cache.set` and :meth:`~ftrack_api.cache.Cache.remove`
methods.


Managing what gets cached
=========================

The cache system is quite flexible when it comes to controlling what should be
cached.

Consider you have a layered cache where the bottom layer cache should be
persisted between sessions. In this setup you probably don't want the persisted
cache to hold non-persisted values, such as modified entity values or newly
created entities not yet committed to the server. However, you might want the
top level memory cache to hold onto these values.

Here is one way to set this up. First define a new proxy cache that is selective
about what it sets::

    import ftrack_api.inspection


    class SelectiveCache(ftrack_api.cache.ProxyCache):
        '''Proxy cache that won't cache newly created entities.'''

        def set(self, key, value):
            '''Set *value* for *key*.'''
            if isinstance(value, ftrack_api.entity.base.Entity):
                if (
                    ftrack_api.inspection.state(value)
                    is ftrack_api.symbol.CREATED
                ):
                    return

            super(SelectiveCache, self).set(key, value)

Now use this custom cache to wrap the serialised cache in the setup above:

.. code-block:: python
    :emphasize-lines: 3, 9

    def cache_maker(session):
        '''Return cache to use for *session*.'''
        return SelectiveCache(
            ftrack_api.cache.SerialisedCache(
                ftrack_api.cache.FileCache(cache_path),
                encode=session.encode,
                decode=session.decode
            )
        )

Now to prevent modified attributes also being persisted, tweak the encode
settings for the file cache:

.. code-block:: python
    :emphasize-lines: 1, 9-12

    import functools


    def cache_maker(session):
        '''Return cache to use for *session*.'''
        return SelectiveCache(
            ftrack_api.cache.SerialisedCache(
                ftrack_api.cache.FileCache(cache_path),
                encode=functools.partial(
                    session.encode,
                    entity_attribute_strategy='persisted_only'
                ),
                decode=session.decode
            )
        )

And use the updated cache maker for your session::

    session = ftrack_api.Session(cache=cache_maker)

.. note::

    For some type of attributes that are computed, long term caching is not
    recommended and such values will not be encoded with the `persisted_only`
    strategy.
