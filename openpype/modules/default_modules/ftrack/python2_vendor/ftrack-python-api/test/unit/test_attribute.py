# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import pytest

import ftrack_api.attribute
import ftrack_api.exception


@pytest.mark.parametrize('attributes', [
    [],
    [ftrack_api.attribute.Attribute('test')]
], ids=[
    'no initial attributes',
    'with initial attributes'
])
def test_initialise_attributes_collection(attributes):
    '''Initialise attributes collection.'''
    attribute_collection = ftrack_api.attribute.Attributes(attributes)
    assert sorted(list(attribute_collection)) == sorted(attributes)


def test_add_attribute_to_attributes_collection():
    '''Add valid attribute to attributes collection.'''
    attribute_collection = ftrack_api.attribute.Attributes()
    attribute = ftrack_api.attribute.Attribute('test')

    assert attribute_collection.keys() == []
    attribute_collection.add(attribute)
    assert attribute_collection.keys() == ['test']


def test_add_duplicate_attribute_to_attributes_collection():
    '''Fail to add attribute with duplicate name to attributes collection.'''
    attribute_collection = ftrack_api.attribute.Attributes()
    attribute = ftrack_api.attribute.Attribute('test')

    attribute_collection.add(attribute)
    with pytest.raises(ftrack_api.exception.NotUniqueError):
        attribute_collection.add(attribute)


def test_remove_attribute_from_attributes_collection():
    '''Remove attribute from attributes collection.'''
    attribute_collection = ftrack_api.attribute.Attributes()
    attribute = ftrack_api.attribute.Attribute('test')

    attribute_collection.add(attribute)
    assert len(attribute_collection) == 1

    attribute_collection.remove(attribute)
    assert len(attribute_collection) == 0


def test_remove_missing_attribute_from_attributes_collection():
    '''Fail to remove attribute not present in attributes collection.'''
    attribute_collection = ftrack_api.attribute.Attributes()
    attribute = ftrack_api.attribute.Attribute('test')

    with pytest.raises(KeyError):
        attribute_collection.remove(attribute)


def test_get_attribute_from_attributes_collection():
    '''Get attribute from attributes collection.'''
    attribute_collection = ftrack_api.attribute.Attributes()
    attribute = ftrack_api.attribute.Attribute('test')
    attribute_collection.add(attribute)

    retrieved_attribute = attribute_collection.get('test')

    assert retrieved_attribute is attribute


def test_get_missing_attribute_from_attributes_collection():
    '''Get attribute not present in attributes collection.'''
    attribute_collection = ftrack_api.attribute.Attributes()
    assert attribute_collection.get('test') is None


@pytest.mark.parametrize('attributes, expected', [
    ([], []),
    ([ftrack_api.attribute.Attribute('test')], ['test'])
], ids=[
    'no initial attributes',
    'with initial attributes'
])
def test_attribute_collection_keys(attributes, expected):
    '''Retrieve keys for attribute collection.'''
    attribute_collection = ftrack_api.attribute.Attributes(attributes)
    assert sorted(attribute_collection.keys()) == sorted(expected)


@pytest.mark.parametrize('attribute, expected', [
    (None, False),
    (ftrack_api.attribute.Attribute('b'), True),
    (ftrack_api.attribute.Attribute('c'), False)
], ids=[
    'none attribute',
    'present attribute',
    'missing attribute'
])
def test_attributes_collection_contains(attribute, expected):
    '''Check presence in attributes collection.'''
    attribute_collection = ftrack_api.attribute.Attributes([
        ftrack_api.attribute.Attribute('a'),
        ftrack_api.attribute.Attribute('b')
    ])

    assert (attribute in attribute_collection) is expected


@pytest.mark.parametrize('attributes, expected', [
    ([], 0),
    ([ftrack_api.attribute.Attribute('test')], 1),
    (
        [
            ftrack_api.attribute.Attribute('a'),
            ftrack_api.attribute.Attribute('b')
        ],
        2
    )
], ids=[
    'no attributes',
    'single attribute',
    'multiple attributes'
])
def test_attributes_collection_count(attributes, expected):
    '''Count attributes in attributes collection.'''
    attribute_collection = ftrack_api.attribute.Attributes(attributes)
    assert len(attribute_collection) == expected


def test_iterate_over_attributes_collection():
    '''Iterate over attributes collection.'''
    attributes = [
        ftrack_api.attribute.Attribute('a'),
        ftrack_api.attribute.Attribute('b')
    ]

    attribute_collection = ftrack_api.attribute.Attributes(attributes)
    for attribute in attribute_collection:
        attributes.remove(attribute)

    assert len(attributes) == 0

