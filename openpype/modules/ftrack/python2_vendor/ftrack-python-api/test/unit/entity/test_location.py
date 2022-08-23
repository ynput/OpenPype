# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import os
import base64
import filecmp

import pytest
import requests

import ftrack_api.exception
import ftrack_api.accessor.disk
import ftrack_api.structure.origin
import ftrack_api.structure.id
import ftrack_api.entity.location
import ftrack_api.resource_identifier_transformer.base as _transformer
import ftrack_api.symbol


class Base64ResourceIdentifierTransformer(
    _transformer.ResourceIdentifierTransformer
):
    '''Resource identifier transformer for test purposes.

    Store resource identifier as base 64 encoded string.

    '''

    def encode(self, resource_identifier, context=None):
        '''Return encoded *resource_identifier* for storing centrally.

        A mapping of *context* values may be supplied to guide the
        transformation.

        '''
        return base64.encodestring(resource_identifier)

    def decode(self, resource_identifier, context=None):
        '''Return decoded *resource_identifier* for use locally.

        A mapping of *context* values may be supplied to guide the
        transformation.

        '''
        return base64.decodestring(resource_identifier)


@pytest.fixture()
def new_location(request, session, unique_name, temporary_directory):
    '''Return new managed location.'''
    location = session.create('Location', {
        'name': 'test-location-{}'.format(unique_name)
    })

    location.accessor = ftrack_api.accessor.disk.DiskAccessor(
        prefix=os.path.join(temporary_directory, 'location')
    )
    location.structure = ftrack_api.structure.id.IdStructure()
    location.priority = 10

    session.commit()

    def cleanup():
        '''Remove created entity.'''
        # First auto-remove all components in location.
        for location_component in location['location_components']:
            session.delete(location_component)

        # At present, need this intermediate commit otherwise server errors
        # complaining that location still has components in it.
        session.commit()

        session.delete(location)
        session.commit()

    request.addfinalizer(cleanup)

    return location


@pytest.fixture()
def new_unmanaged_location(request, session, unique_name):
    '''Return new unmanaged location.'''
    location = session.create('Location', {
        'name': 'test-location-{}'.format(unique_name)
    })

    # TODO: Change to managed and use a temporary directory cleaned up after.
    ftrack_api.mixin(
        location, ftrack_api.entity.location.UnmanagedLocationMixin,
        name='UnmanagedTestLocation'
    )
    location.accessor = ftrack_api.accessor.disk.DiskAccessor(prefix='')
    location.structure = ftrack_api.structure.origin.OriginStructure()
    location.priority = 10

    session.commit()

    def cleanup():
        '''Remove created entity.'''
        # First auto-remove all components in location.
        for location_component in location['location_components']:
            session.delete(location_component)

        # At present, need this intermediate commit otherwise server errors
        # complaining that location still has components in it.
        session.commit()

        session.delete(location)
        session.commit()

    request.addfinalizer(cleanup)

    return location


@pytest.fixture()
def origin_location(session):
    '''Return origin location.'''
    return session.query('Location where name is "ftrack.origin"').one()

@pytest.fixture()
def server_location(session):
    '''Return server location.'''
    return session.get('Location', ftrack_api.symbol.SERVER_LOCATION_ID)


@pytest.fixture()
def server_image_component(request, session, server_location):
    image_file = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            '..',
            'fixture',
            'media',
            'image.png'
        )
    )
    component = session.create_component(
        image_file, location=server_location
    )

    def cleanup():
        server_location.remove_component(component)
    request.addfinalizer(cleanup)

    return component


@pytest.mark.parametrize('name', [
    'named',
    None
], ids=[
    'named',
    'unnamed'
])
def test_string_representation(session, name):
    '''Return string representation.'''
    location = session.create('Location', {'id': '1'})
    if name:
        location['name'] = name
        assert str(location) == '<Location("named", 1)>'
    else:
        assert str(location) == '<Location(1)>'


def test_add_components(new_location, origin_location, session, temporary_file):
    '''Add components.'''
    component_a = session.create_component(
        temporary_file, location=None
    )
    component_b = session.create_component(
        temporary_file, location=None
    )

    assert (
        new_location.get_component_availabilities([component_a, component_b])
        == [0.0, 0.0]
    )

    new_location.add_components(
        [component_a, component_b], [origin_location, origin_location]
    )

    # Recalculate availability.

    # Currently have to manually expire the related attribute. This should be
    # solved in future by bi-directional relationship updating.
    del component_a['component_locations']
    del component_b['component_locations']

    assert (
        new_location.get_component_availabilities([component_a, component_b])
        == [100.0, 100.0]
    )


def test_add_components_from_single_location(
    new_location, origin_location, session, temporary_file
):
    '''Add components from single location.'''
    component_a = session.create_component(
        temporary_file, location=None
    )
    component_b = session.create_component(
        temporary_file, location=None
    )

    assert (
        new_location.get_component_availabilities([component_a, component_b])
        == [0.0, 0.0]
    )

    new_location.add_components([component_a, component_b], origin_location)

    # Recalculate availability.

    # Currently have to manually expire the related attribute. This should be
    # solved in future by bi-directional relationship updating.
    del component_a['component_locations']
    del component_b['component_locations']

    assert (
        new_location.get_component_availabilities([component_a, component_b])
        == [100.0, 100.0]
    )


def test_add_components_with_mismatching_sources(new_location, new_component):
    '''Fail to add components when sources mismatched.'''
    with pytest.raises(ValueError):
        new_location.add_components([new_component], [])


def test_add_components_with_undefined_structure(new_location, mocker):
    '''Fail to add components when location structure undefined.'''
    mocker.patch.object(new_location, 'structure', None)

    with pytest.raises(ftrack_api.exception.LocationError):
        new_location.add_components([], [])


def test_add_components_already_in_location(
    session, temporary_file, new_location, new_component, origin_location
):
    '''Fail to add components already in location.'''
    new_location.add_component(new_component, origin_location)

    another_new_component = session.create_component(
        temporary_file, location=None
    )

    with pytest.raises(ftrack_api.exception.ComponentInLocationError):
        new_location.add_components(
            [another_new_component, new_component], origin_location
        )


def test_add_component_when_data_already_exists(
    new_location, new_component, origin_location
):
    '''Fail to add component when data already exists.'''
    # Inject pre-existing data on disk.
    resource_identifier = new_location.structure.get_resource_identifier(
        new_component
    )
    container = new_location.accessor.get_container(resource_identifier)
    new_location.accessor.make_container(container)
    data = new_location.accessor.open(resource_identifier, 'w')
    data.close()

    with pytest.raises(ftrack_api.exception.LocationError):
        new_location.add_component(new_component, origin_location)


def test_add_component_missing_source_accessor(
    new_location, new_component, origin_location, mocker
):
    '''Fail to add component when source is missing accessor.'''
    mocker.patch.object(origin_location, 'accessor', None)

    with pytest.raises(ftrack_api.exception.LocationError):
        new_location.add_component(new_component, origin_location)


def test_add_component_missing_target_accessor(
    new_location, new_component, origin_location, mocker
):
    '''Fail to add component when target is missing accessor.'''
    mocker.patch.object(new_location, 'accessor', None)

    with pytest.raises(ftrack_api.exception.LocationError):
        new_location.add_component(new_component, origin_location)


def test_add_container_component(
    new_container_component, new_location, origin_location
):
    '''Add container component.'''
    new_location.add_component(new_container_component, origin_location)

    assert (
        new_location.get_component_availability(new_container_component)
        == 100.0
    )


def test_add_sequence_component_recursively(
    new_sequence_component, new_location, origin_location
):
    '''Add sequence component recursively.'''
    new_location.add_component(
        new_sequence_component, origin_location, recursive=True
    )

    assert (
        new_location.get_component_availability(new_sequence_component)
        == 100.0
    )


def test_add_sequence_component_non_recursively(
    new_sequence_component, new_location, origin_location
):
    '''Add sequence component non recursively.'''
    new_location.add_component(
        new_sequence_component, origin_location, recursive=False
    )

    assert (
        new_location.get_component_availability(new_sequence_component)
        == 0.0
    )


def test_remove_components(
    session, new_location, origin_location, temporary_file
):
    '''Remove components.'''
    component_a = session.create_component(
        temporary_file, location=None
    )
    component_b = session.create_component(
        temporary_file, location=None
    )

    new_location.add_components([component_a, component_b], origin_location)
    assert (
        new_location.get_component_availabilities([component_a, component_b])
        == [100.0, 100.0]
    )

    new_location.remove_components([
        component_a, component_b
    ])

    # Recalculate availability.

    # Currently have to manually expire the related attribute. This should be
    # solved in future by bi-directional relationship updating.
    del component_a['component_locations']
    del component_b['component_locations']

    assert (
        new_location.get_component_availabilities([component_a, component_b])
        == [0.0, 0.0]
    )


def test_remove_sequence_component_recursively(
    new_sequence_component, new_location, origin_location
):
    '''Remove sequence component recursively.'''
    new_location.add_component(
        new_sequence_component, origin_location, recursive=True
    )

    new_location.remove_component(
        new_sequence_component, recursive=True
    )

    assert (
        new_location.get_component_availability(new_sequence_component)
        == 0.0
    )


def test_remove_sequence_component_non_recursively(
    new_sequence_component, new_location, origin_location
):
    '''Remove sequence component non recursively.'''
    new_location.add_component(
        new_sequence_component, origin_location, recursive=False
    )

    new_location.remove_component(
        new_sequence_component, recursive=False
    )

    assert (
        new_location.get_component_availability(new_sequence_component)
        == 0.0
    )


def test_remove_component_missing_accessor(
    new_location, new_component, origin_location, mocker
):
    '''Fail to remove component when location is missing accessor.'''
    new_location.add_component(new_component, origin_location)
    mocker.patch.object(new_location, 'accessor', None)

    with pytest.raises(ftrack_api.exception.LocationError):
        new_location.remove_component(new_component)


def test_resource_identifier_transformer(
    new_component, new_unmanaged_location, origin_location, mocker
):
    '''Transform resource identifier.'''
    session = new_unmanaged_location.session

    transformer = Base64ResourceIdentifierTransformer(session)
    mocker.patch.object(
        new_unmanaged_location, 'resource_identifier_transformer', transformer
    )

    new_unmanaged_location.add_component(new_component, origin_location)

    original_resource_identifier = origin_location.get_resource_identifier(
        new_component
    )
    assert (
        new_component['component_locations'][0]['resource_identifier']
        == base64.encodestring(original_resource_identifier)
    )

    assert (
        new_unmanaged_location.get_resource_identifier(new_component)
        == original_resource_identifier
    )


def test_get_filesystem_path(new_component, new_location, origin_location):
    '''Retrieve filesystem path.'''
    new_location.add_component(new_component, origin_location)
    resource_identifier = new_location.structure.get_resource_identifier(
        new_component
    )
    expected = os.path.normpath(
        os.path.join(new_location.accessor.prefix, resource_identifier)
    )
    assert new_location.get_filesystem_path(new_component) == expected


def test_get_context(new_component, new_location, origin_location):
    '''Retrieve context for component.'''
    resource_identifier = origin_location.get_resource_identifier(
        new_component
    )
    context = new_location._get_context(new_component, origin_location)
    assert context == {
        'source_resource_identifier': resource_identifier
    }


def test_get_context_for_component_not_in_source(new_component, new_location):
    '''Retrieve context for component not in source location.'''
    context = new_location._get_context(new_component, new_location)
    assert context == {}


def test_data_transfer(session, new_location, origin_location):
    '''Transfer a real file and make sure it is identical.'''
    video_file = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            '..',
            'fixture',
            'media',
            'colour_wheel.mov'
        )
    )
    component = session.create_component(
        video_file, location=new_location
    )
    new_video_file = new_location.get_filesystem_path(component)

    assert filecmp.cmp(video_file, new_video_file)


def test_get_thumbnail_url(server_location, server_image_component):
    '''Test download a thumbnail image from server location'''
    thumbnail_url = server_location.get_thumbnail_url(
        server_image_component,
        size=10
    )
    assert thumbnail_url

    response = requests.get(thumbnail_url)
    response.raise_for_status()

    image_file = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            '..',
            'fixture',
            'media',
            'image-resized-10.png'
        )
    )
    expected_image_contents = open(image_file).read()
    assert response.content == expected_image_contents
