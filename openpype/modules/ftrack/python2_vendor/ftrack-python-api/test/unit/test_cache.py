# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import os
import uuid
import tempfile

import pytest

import ftrack_api.cache


@pytest.fixture(params=['proxy', 'layered', 'memory', 'file', 'serialised'])
def cache(request):
    '''Return cache.'''
    if request.param == 'proxy':
        cache = ftrack_api.cache.ProxyCache(
            ftrack_api.cache.MemoryCache()
        )

    elif request.param == 'layered':
        cache = ftrack_api.cache.LayeredCache(
            [ftrack_api.cache.MemoryCache()]
        )

    elif request.param == 'memory':
        cache = ftrack_api.cache.MemoryCache()

    elif request.param == 'file':
        cache_path = os.path.join(
            tempfile.gettempdir(), '{0}.dbm'.format(uuid.uuid4().hex)
        )

        cache = ftrack_api.cache.FileCache(cache_path)

        def cleanup():
            '''Cleanup.'''
            try:
                os.remove(cache_path)
            except OSError:
                # BSD DB (Mac OSX) implementation of the interface will append
                # a .db extension.
                os.remove(cache_path + '.db')

        request.addfinalizer(cleanup)

    elif request.param == 'serialised':
        cache = ftrack_api.cache.SerialisedCache(
            ftrack_api.cache.MemoryCache(),
            encode=lambda value: value,
            decode=lambda value: value
        )

    else:
        raise ValueError(
            'Unrecognised cache fixture type {0!r}'.format(request.param)
        )

    return cache



class Class(object):
    '''Class for testing.'''

    def method(self, key):
        '''Method for testing.'''


def function(mutable, x, y=2):
    '''Function for testing.'''
    mutable['called'] = True
    return {'result': x + y}


def assert_memoised_call(
    memoiser, function, expected, args=None, kw=None, memoised=True
):
    '''Assert *function* call via *memoiser* was *memoised*.'''
    mapping = {'called': False}
    if args is not None:
        args = (mapping,) + args
    else:
        args = (mapping,)

    result = memoiser.call(function, args, kw)

    assert result == expected
    assert mapping['called'] is not memoised


def test_get(cache):
    '''Retrieve item from cache.'''
    cache.set('key', 'value')
    assert cache.get('key') == 'value'


def test_get_missing_key(cache):
    '''Fail to retrieve missing item from cache.'''
    with pytest.raises(KeyError):
        cache.get('key')


def test_set(cache):
    '''Set item in cache.'''
    with pytest.raises(KeyError):
        cache.get('key')

    cache.set('key', 'value')
    assert cache.get('key') == 'value'


def test_remove(cache):
    '''Remove item from cache.'''
    cache.set('key', 'value')
    cache.remove('key')

    with pytest.raises(KeyError):
        cache.get('key')


def test_remove_missing_key(cache):
    '''Fail to remove missing key.'''
    with pytest.raises(KeyError):
        cache.remove('key')


def test_keys(cache):
    '''Retrieve keys of items in cache.'''
    assert cache.keys() == []
    cache.set('a', 'a_value')
    cache.set('b', 'b_value')
    cache.set('c', 'c_value')
    assert sorted(cache.keys()) == sorted(['a', 'b', 'c'])


def test_clear(cache):
    '''Remove items from cache.'''
    cache.set('a', 'a_value')
    cache.set('b', 'b_value')
    cache.set('c', 'c_value')

    assert cache.keys()
    cache.clear()

    assert not cache.keys()


def test_clear_using_pattern(cache):
    '''Remove items that match pattern from cache.'''
    cache.set('matching_key', 'value')
    cache.set('another_matching_key', 'value')
    cache.set('key_not_matching', 'value')

    assert cache.keys()
    cache.clear(pattern='.*matching_key$')

    assert cache.keys() == ['key_not_matching']


def test_clear_encountering_missing_key(cache, mocker):
    '''Clear missing key.'''
    # Force reporting keys that are not actually valid for test purposes.
    mocker.patch.object(cache, 'keys', lambda: ['missing'])
    assert cache.keys() == ['missing']

    # Should not error even though key not valid.
    cache.clear()

    # The key was not successfully removed so should still be present.
    assert cache.keys() == ['missing']


def test_layered_cache_propagates_value_on_get():
    '''Layered cache propagates value on get.'''
    caches = [
        ftrack_api.cache.MemoryCache(),
        ftrack_api.cache.MemoryCache(),
        ftrack_api.cache.MemoryCache()
    ]

    cache = ftrack_api.cache.LayeredCache(caches)

    # Set item on second level cache only.
    caches[1].set('key', 'value')

    # Retrieving key via layered cache should propagate it automatically to
    # higher level caches only.
    assert cache.get('key') == 'value'
    assert caches[0].get('key') == 'value'

    with pytest.raises(KeyError):
        caches[2].get('key')


def test_layered_cache_remove_at_depth():
    '''Remove key that only exists at depth in LayeredCache.'''
    caches = [
        ftrack_api.cache.MemoryCache(),
        ftrack_api.cache.MemoryCache()
    ]

    cache = ftrack_api.cache.LayeredCache(caches)

    # Set item on second level cache only.
    caches[1].set('key', 'value')

    # Removing key that only exists at depth should not raise key error.
    cache.remove('key')

    # Ensure key was removed.
    assert not cache.keys()


def test_expand_references():
    '''Test that references are expanded from serialized cache.'''

    cache_path = os.path.join(
        tempfile.gettempdir(), '{0}.dbm'.format(uuid.uuid4().hex)
    )

    def make_cache(session, cache_path):
        '''Create a serialised file cache.'''
        serialized_file_cache = ftrack_api.cache.SerialisedCache(
            ftrack_api.cache.FileCache(cache_path),
            encode=session.encode,
            decode=session.decode
        )

        return serialized_file_cache

    # Populate the serialized file cache.
    session = ftrack_api.Session(
        cache=lambda session, cache_path=cache_path:make_cache(
            session, cache_path
        )
    )

    expanded_results = dict()

    query_string = 'select asset.parent from AssetVersion where asset is_not None limit 10'

    for sequence in session.query(query_string):
        asset = sequence.get('asset')

        expanded_results.setdefault(
            asset.get('id'), asset.get('parent')
        )

    # Fetch the data from cache.
    new_session = ftrack_api.Session(
        cache=lambda session, cache_path=cache_path:make_cache(
            session, cache_path
        )
    )


    new_session_two = ftrack_api.Session(
        cache=lambda session, cache_path=cache_path:make_cache(
            session, cache_path
        )
    )


    # Make sure references are merged.
    for sequence in new_session.query(query_string):
        asset = sequence.get('asset')

        assert (
            asset.get('parent') == expanded_results[asset.get('id')]
        )

        # Use for fetching directly using get.
        assert (
            new_session_two.get(asset.entity_type, asset.get('id')).get('parent') ==
            expanded_results[asset.get('id')]
        )



@pytest.mark.parametrize('items, key', [
    (({},), '{}'),
    (({}, {}), '{}{}')
], ids=[
    'single object',
    'multiple objects'
])
def test_string_key_maker_key(items, key):
    '''Generate key using string key maker.'''
    key_maker = ftrack_api.cache.StringKeyMaker()
    assert key_maker.key(*items) == key


@pytest.mark.parametrize('items, key', [
    (
        ({},),
        '\x01\x01'
    ),
    (
        ({'a': 'b'}, [1, 2]),
        '\x01'
            '\x80\x02U\x01a.' '\x02' '\x80\x02U\x01b.'
        '\x01'
        '\x00'
        '\x03'
            '\x80\x02K\x01.' '\x00' '\x80\x02K\x02.'
        '\x03'
    ),
    (
        (function,),
        '\x04function\x00unit.test_cache'
    ),
    (
        (Class,),
        '\x04Class\x00unit.test_cache'
    ),
    (
        (Class.method,),
        '\x04method\x00Class\x00unit.test_cache'
    ),
    (
        (callable,),
        '\x04callable'
    )
], ids=[
    'single mapping',
    'multiple objects',
    'function',
    'class',
    'method',
    'builtin'
])
def test_object_key_maker_key(items, key):
    '''Generate key using string key maker.'''
    key_maker = ftrack_api.cache.ObjectKeyMaker()
    assert key_maker.key(*items) == key


def test_memoised_call():
    '''Call memoised function.'''
    memoiser = ftrack_api.cache.Memoiser()

    # Initial call should not be memoised so function is executed.
    assert_memoised_call(
        memoiser, function, args=(1,), expected={'result': 3}, memoised=False
    )

    # Identical call should be memoised so function is not executed again.
    assert_memoised_call(
        memoiser, function, args=(1,), expected={'result': 3}, memoised=True
    )

    # Differing call is not memoised so function is executed.
    assert_memoised_call(
        memoiser, function, args=(3,), expected={'result': 5}, memoised=False
    )


def test_memoised_call_variations():
    '''Call memoised function with identical arguments using variable format.'''
    memoiser = ftrack_api.cache.Memoiser()
    expected = {'result': 3}

    # Call function once to ensure is memoised.
    assert_memoised_call(
        memoiser, function, args=(1,), expected=expected, memoised=False
    )

    # Each of the following calls should equate to the same key and make
    # use of the memoised value.
    for args, kw in [
        ((), {'x': 1}),
        ((), {'x': 1, 'y': 2}),
        ((1,), {'y': 2}),
        ((1,), {})
    ]:
        assert_memoised_call(
            memoiser, function, args=args, kw=kw, expected=expected
        )

    # The following calls should all be treated as new variations and so
    # not use any memoised value.
    assert_memoised_call(
        memoiser, function, kw={'x': 2}, expected={'result': 4}, memoised=False
    )
    assert_memoised_call(
        memoiser, function, kw={'x': 3, 'y': 2}, expected={'result': 5},
        memoised=False
    )
    assert_memoised_call(
        memoiser, function, args=(4, ), kw={'y': 2}, expected={'result': 6},
        memoised=False
    )
    assert_memoised_call(
        memoiser, function, args=(5, ), expected={'result': 7}, memoised=False
    )


def test_memoised_mutable_return_value():
    '''Avoid side effects for returned mutable arguments when memoising.'''
    memoiser = ftrack_api.cache.Memoiser()
    arguments = ({'called': False}, 1)

    result_a = memoiser.call(function, arguments)
    assert result_a == {'result': 3}
    assert arguments[0]['called']

    # Modify mutable externally and check that stored memoised value is
    # unchanged.
    del result_a['result']

    arguments[0]['called'] = False
    result_b = memoiser.call(function, arguments)

    assert result_b == {'result': 3}
    assert not arguments[0]['called']
