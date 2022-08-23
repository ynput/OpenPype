# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import inspect

import pytest


@pytest.mark.parametrize('schema, expected', [
    ('Task', [
        'Not started', 'In progress', 'Awaiting approval', 'Approved'
    ]),
    ('Shot', [
        'Normal', 'Omitted', 'On Hold'
    ]),
    ('AssetVersion', [
        'Approved', 'Pending'
    ]),
    ('AssetBuild', [
        'Normal', 'Omitted', 'On Hold'
    ]),
    ('Invalid', ValueError)
], ids=[
    'task',
    'shot',
    'asset version',
    'asset build',
    'invalid'
])
def test_get_statuses(project_schema, schema, expected):
    '''Retrieve statuses for schema and optional type.'''
    if inspect.isclass(expected) and issubclass(expected, Exception):
        with pytest.raises(expected):
            project_schema.get_statuses(schema)

    else:
        statuses = project_schema.get_statuses(schema)
        status_names = [status['name'] for status in statuses]
        assert sorted(status_names) == sorted(expected)


@pytest.mark.parametrize('schema, expected', [
    ('Task', [
        'Generic', 'Animation', 'Modeling', 'Previz', 'Lookdev', 'Hair',
        'Cloth', 'FX', 'Lighting', 'Compositing', 'Tracking', 'Rigging',
        'test 1', 'test type 2'
    ]),
    ('AssetBuild', ['Character', 'Prop', 'Environment', 'Matte Painting']),
    ('Invalid', ValueError)
], ids=[
    'task',
    'asset build',
    'invalid'
])
def test_get_types(project_schema, schema, expected):
    '''Retrieve types for schema.'''
    if inspect.isclass(expected) and issubclass(expected, Exception):
        with pytest.raises(expected):
            project_schema.get_types(schema)

    else:
        types = project_schema.get_types(schema)
        type_names = [type_['name'] for type_ in types]
        assert sorted(type_names) == sorted(expected)
