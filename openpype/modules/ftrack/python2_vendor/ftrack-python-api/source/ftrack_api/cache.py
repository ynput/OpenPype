# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

'''Caching framework.

Defines a standardised :class:`Cache` interface for storing data against
specific keys. Key generation is also standardised using a :class:`KeyMaker`
interface.

Combining a Cache and KeyMaker allows for memoisation of function calls with
respect to the arguments used by using a :class:`Memoiser`.

As a convenience a simple :func:`memoise` decorator is included for quick
memoisation of function using a global cache and standard key maker.

'''

import collections
import functools
import abc
import copy
import inspect
import re
import anydbm
import contextlib
try:
    import cPickle as pickle
except ImportError:  # pragma: no cover
    import pickle

import ftrack_api.inspection
import ftrack_api.symbol


class Cache(object):
    '''Cache interface.

    Derive from this to define concrete cache implementations. A cache is
    centered around the concept of key:value pairings where the key is unique
    across the cache.

    '''

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get(self, key):
        '''Return value for *key*.

        Raise :exc:`KeyError` if *key* not found.

        '''

    @abc.abstractmethod
    def set(self, key, value):
        '''Set *value* for *key*.'''

    @abc.abstractmethod
    def remove(self, key):
        '''Remove *key* and return stored value.

        Raise :exc:`KeyError` if *key* not found.

        '''

    def keys(self):
        '''Return list of keys at this current time.

        .. warning::

            Actual keys may differ from those returned due to timing of access.

        '''
        raise NotImplementedError()  # pragma: no cover

    def values(self):
        '''Return values for current keys.'''
        values = []
        for key in self.keys():
            try:
                value = self.get(key)
            except KeyError:
                continue
            else:
                values.append(value)

        return values

    def clear(self, pattern=None):
        '''Remove all keys matching *pattern*.

        *pattern* should be a regular expression string.

        If *pattern* is None then all keys will be removed.

        '''
        if pattern is not None:
            pattern = re.compile(pattern)

        for key in self.keys():
            if pattern is not None:
                if not pattern.search(key):
                    continue

            try:
                self.remove(key)
            except KeyError:
                pass


class ProxyCache(Cache):
    '''Proxy another cache.'''

    def __init__(self, proxied):
        '''Initialise cache with *proxied* cache instance.'''
        self.proxied = proxied
        super(ProxyCache, self).__init__()

    def get(self, key):
        '''Return value for *key*.

        Raise :exc:`KeyError` if *key* not found.

        '''
        return self.proxied.get(key)

    def set(self, key, value):
        '''Set *value* for *key*.'''
        return self.proxied.set(key, value)

    def remove(self, key):
        '''Remove *key* and return stored value.

        Raise :exc:`KeyError` if *key* not found.

        '''
        return self.proxied.remove(key)

    def keys(self):
        '''Return list of keys at this current time.

        .. warning::

            Actual keys may differ from those returned due to timing of access.

        '''
        return self.proxied.keys()


class LayeredCache(Cache):
    '''Layered cache.'''

    def __init__(self, caches):
        '''Initialise cache with *caches*.'''
        super(LayeredCache, self).__init__()
        self.caches = caches

    def get(self, key):
        '''Return value for *key*.

        Raise :exc:`KeyError` if *key* not found.

        Attempt to retrieve from cache layers in turn, starting with shallowest.
        If value retrieved, then also set the value in each higher level cache
        up from where retrieved.

        '''
        target_caches = []
        value = ftrack_api.symbol.NOT_SET

        for cache in self.caches:
            try:
                value = cache.get(key)
            except KeyError:
                target_caches.append(cache)
                continue
            else:
                break

        if value is ftrack_api.symbol.NOT_SET:
            raise KeyError(key)

        # Set value on all higher level caches.
        for cache in target_caches:
            cache.set(key, value)

        return value

    def set(self, key, value):
        '''Set *value* for *key*.'''
        for cache in self.caches:
            cache.set(key, value)

    def remove(self, key):
        '''Remove *key*.

        Raise :exc:`KeyError` if *key* not found in any layer.

        '''
        removed = False
        for cache in self.caches:
            try:
                cache.remove(key)
            except KeyError:
                pass
            else:
                removed = True

        if not removed:
            raise KeyError(key)

    def keys(self):
        '''Return list of keys at this current time.

        .. warning::

            Actual keys may differ from those returned due to timing of access.

        '''
        keys = []
        for cache in self.caches:
            keys.extend(cache.keys())

        return list(set(keys))


class MemoryCache(Cache):
    '''Memory based cache.'''

    def __init__(self):
        '''Initialise cache.'''
        self._cache = {}
        super(MemoryCache, self).__init__()

    def get(self, key):
        '''Return value for *key*.

        Raise :exc:`KeyError` if *key* not found.

        '''
        return self._cache[key]

    def set(self, key, value):
        '''Set *value* for *key*.'''
        self._cache[key] = value

    def remove(self, key):
        '''Remove *key*.

        Raise :exc:`KeyError` if *key* not found.

        '''
        del self._cache[key]

    def keys(self):
        '''Return list of keys at this current time.

        .. warning::

            Actual keys may differ from those returned due to timing of access.

        '''
        return self._cache.keys()


class FileCache(Cache):
    '''File based cache that uses :mod:`anydbm` module.

    .. note::

        No locking of the underlying file is performed.

    '''

    def __init__(self, path):
        '''Initialise cache at *path*.'''
        self.path = path

        # Initialise cache.
        cache = anydbm.open(self.path, 'c')
        cache.close()

        super(FileCache, self).__init__()

    @contextlib.contextmanager
    def _database(self):
        '''Yield opened database file.'''
        cache = anydbm.open(self.path, 'w')
        try:
            yield cache
        finally:
            cache.close()

    def get(self, key):
        '''Return value for *key*.

        Raise :exc:`KeyError` if *key* not found.

        '''
        with self._database() as cache:
            return cache[key]

    def set(self, key, value):
        '''Set *value* for *key*.'''
        with self._database() as cache:
            cache[key] = value

    def remove(self, key):
        '''Remove *key*.

        Raise :exc:`KeyError` if *key* not found.

        '''
        with self._database() as cache:
            del cache[key]

    def keys(self):
        '''Return list of keys at this current time.

        .. warning::

            Actual keys may differ from those returned due to timing of access.

        '''
        with self._database() as cache:
            return cache.keys()


class SerialisedCache(ProxyCache):
    '''Proxied cache that stores values as serialised data.'''

    def __init__(self, proxied, encode=None, decode=None):
        '''Initialise cache with *encode* and *decode* callables.

        *proxied* is the underlying cache to use for storage.

        '''
        self.encode = encode
        self.decode = decode
        super(SerialisedCache, self).__init__(proxied)

    def get(self, key):
        '''Return value for *key*.

        Raise :exc:`KeyError` if *key* not found.

        '''
        value = super(SerialisedCache, self).get(key)
        if self.decode:
            value = self.decode(value)

        return value

    def set(self, key, value):
        '''Set *value* for *key*.'''
        if self.encode:
            value = self.encode(value)

        super(SerialisedCache, self).set(key, value)


class KeyMaker(object):
    '''Generate unique keys.'''

    __metaclass__ = abc.ABCMeta

    def __init__(self):
        '''Initialise key maker.'''
        super(KeyMaker, self).__init__()
        self.item_separator = ''

    def key(self, *items):
        '''Return key for *items*.'''
        keys = []
        for item in items:
            keys.append(self._key(item))

        return self.item_separator.join(keys)

    @abc.abstractmethod
    def _key(self, obj):
        '''Return key for *obj*.'''


class StringKeyMaker(KeyMaker):
    '''Generate string key.'''

    def _key(self, obj):
        '''Return key for *obj*.'''
        return str(obj)


class ObjectKeyMaker(KeyMaker):
    '''Generate unique keys for objects.'''

    def __init__(self):
        '''Initialise key maker.'''
        super(ObjectKeyMaker, self).__init__()
        self.item_separator = '\0'
        self.mapping_identifier = '\1'
        self.mapping_pair_separator = '\2'
        self.iterable_identifier = '\3'
        self.name_identifier = '\4'

    def _key(self, item):
        '''Return key for *item*.

        Returned key will be a pickle like string representing the *item*. This
        allows for typically non-hashable objects to be used in key generation
        (such as dictionaries).

        If *item* is iterable then each item in it shall also be passed to this
        method to ensure correct key generation.

        Special markers are used to distinguish handling of specific cases in
        order to ensure uniqueness of key corresponds directly to *item*.

        Example::

            >>> key_maker = ObjectKeyMaker()
            >>> def add(x, y):
            ...     "Return sum of *x* and *y*."
            ...     return x + y
            ...
            >>> key_maker.key(add, (1, 2))
            '\x04add\x00__main__\x00\x03\x80\x02K\x01.\x00\x80\x02K\x02.\x03'
            >>> key_maker.key(add, (1, 3))
            '\x04add\x00__main__\x00\x03\x80\x02K\x01.\x00\x80\x02K\x03.\x03'

        '''
        # TODO: Consider using a more robust and comprehensive solution such as
        # dill (https://github.com/uqfoundation/dill).
        if isinstance(item, collections.Iterable):
            if isinstance(item, basestring):
                return pickle.dumps(item, pickle.HIGHEST_PROTOCOL)

            if isinstance(item, collections.Mapping):
                contents = self.item_separator.join([
                    (
                        self._key(key) +
                        self.mapping_pair_separator +
                        self._key(value)
                    )
                    for key, value in sorted(item.items())
                ])
                return (
                    self.mapping_identifier +
                    contents +
                    self.mapping_identifier
                )

            else:
                contents = self.item_separator.join([
                    self._key(item) for item in item
                ])
                return (
                    self.iterable_identifier +
                    contents +
                    self.iterable_identifier
                )

        elif inspect.ismethod(item):
            return ''.join((
                self.name_identifier,
                item.__name__,
                self.item_separator,
                item.im_class.__name__,
                self.item_separator,
                item.__module__
            ))

        elif inspect.isfunction(item) or inspect.isclass(item):
            return ''.join((
                self.name_identifier,
                item.__name__,
                self.item_separator,
                item.__module__
            ))

        elif inspect.isbuiltin(item):
            return self.name_identifier + item.__name__

        else:
            return pickle.dumps(item, pickle.HIGHEST_PROTOCOL)


class Memoiser(object):
    '''Memoise function calls using a :class:`KeyMaker` and :class:`Cache`.

    Example::

        >>> memoiser = Memoiser(MemoryCache(), ObjectKeyMaker())
        >>> def add(x, y):
        ...     "Return sum of *x* and *y*."
        ...     print 'Called'
        ...     return x + y
        ...
        >>> memoiser.call(add, (1, 2), {})
        Called
        >>> memoiser.call(add, (1, 2), {})
        >>> memoiser.call(add, (1, 3), {})
        Called

    '''

    def __init__(self, cache=None, key_maker=None, return_copies=True):
        '''Initialise with *cache* and *key_maker* to use.

        If *cache* is not specified a default :class:`MemoryCache` will be
        used. Similarly, if *key_maker* is not specified a default
        :class:`ObjectKeyMaker` will be used.

        If *return_copies* is True then all results returned from the cache will
        be deep copies to avoid indirect mutation of cached values.

        '''
        self.cache = cache
        if self.cache is None:
            self.cache = MemoryCache()

        self.key_maker = key_maker
        if self.key_maker is None:
            self.key_maker = ObjectKeyMaker()

        self.return_copies = return_copies
        super(Memoiser, self).__init__()

    def call(self, function, args=None, kw=None):
        '''Call *function* with *args* and *kw* and return result.

        If *function* was previously called with exactly the same arguments
        then return cached result if available.

        Store result for call in cache.

        '''
        if args is None:
            args = ()

        if kw is None:
            kw = {}

        # Support arguments being passed as positionals or keywords.
        arguments = inspect.getcallargs(function, *args, **kw)

        key = self.key_maker.key(function, arguments)
        try:
            value = self.cache.get(key)

        except KeyError:
            value = function(*args, **kw)
            self.cache.set(key, value)

        # If requested, deep copy value to return in order to avoid cached value
        # being inadvertently altered by the caller.
        if self.return_copies:
            value = copy.deepcopy(value)

        return value


def memoise_decorator(memoiser):
    '''Decorator to memoise function calls using *memoiser*.'''
    def outer(function):

        @functools.wraps(function)
        def inner(*args, **kw):
            return memoiser.call(function, args, kw)

        return inner

    return outer


#: Default memoiser.
memoiser = Memoiser()

#: Default memoise decorator using standard cache and key maker.
memoise = memoise_decorator(memoiser)
