# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack
import os

import pytest


def test_get_availability(new_component):
    '''Retrieve availability in locations.'''
    session = new_component.session
    availability = new_component.get_availability()

    # Note: Currently the origin location is also 0.0 as the link is not
    # persisted to the server. This may change in future and this test would
    # need updating as a result.
    assert set(availability.values()) == set([0.0])

    # Add to a location.
    source_location = session.query(
        'Location where name is "ftrack.origin"'
    ).one()

    target_location = session.query(
        'Location where name is "ftrack.unmanaged"'
    ).one()

    target_location.add_component(new_component, source_location)

    # Recalculate availability.

    # Currently have to manually expire the related attribute. This should be
    # solved in future by bi-directional relationship updating.
    del new_component['component_locations']

    availability = new_component.get_availability()
    target_availability = availability.pop(target_location['id'])
    assert target_availability == 100.0

    # All other locations should still be 0.
    assert set(availability.values()) == set([0.0])

@pytest.fixture()
def image_path():
    '''Return a path to an image file.'''
    image_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            '..',
            'fixture',
            'media',
            'image.png'
        )
    )

    return image_path

def test_create_task_thumbnail(task, image_path):
    '''Successfully create thumbnail component and set as task thumbnail.'''
    component = task.create_thumbnail(image_path)
    component.session.commit()
    assert component['id'] == task['thumbnail_id']


def test_create_thumbnail_with_data(task, image_path, unique_name):
    '''Successfully create thumbnail component with custom data.'''
    data = {'name': unique_name}
    component = task.create_thumbnail(image_path, data=data)
    component.session.commit()
    assert component['name'] == unique_name
