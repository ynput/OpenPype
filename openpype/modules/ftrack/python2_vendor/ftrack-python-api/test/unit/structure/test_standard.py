# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import uuid

import pytest

import ftrack_api
import ftrack_api.structure.standard


@pytest.fixture(scope='session')
def new_project(request):
    '''Return new empty project.'''
    session = ftrack_api.Session()

    project_schema = session.query('ProjectSchema').first()
    project_name = 'python_api_test_{0}'.format(uuid.uuid1().hex)
    project = session.create('Project', {
        'name': project_name,
        'full_name': project_name + '_full',
        'project_schema': project_schema
    })

    session.commit()

    def cleanup():
        '''Remove created entity.'''
        session.delete(project)
        session.commit()

    request.addfinalizer(cleanup)

    return project


def new_container_component():
    '''Return container component.'''
    session = ftrack_api.Session()

    entity = session.create('ContainerComponent', {
        'name': 'container_component'
    })

    return entity


def new_sequence_component():
    '''Return sequence component.'''
    session = ftrack_api.Session()

    entity = session.create_component(
        '/tmp/foo/%04d.jpg [1-10]', location=None, data={'name': 'baz'}
    )

    return entity


def new_file_component(name='foo', container=None):
    '''Return file component with *name* and *container*.'''
    if container:
        session = container.session
    else:
        session = ftrack_api.Session()

    entity = session.create('FileComponent', {
        'name': name,
        'file_type': '.png',
        'container': container
    })

    return entity


# Reusable fixtures.
file_component = new_file_component()
container_component = new_container_component()
sequence_component = new_sequence_component()


# Note: to improve test performance the same project is reused throughout the
# tests. This means that all hierarchical names must be unique, otherwise an
# IntegrityError will be raised on the server.

@pytest.mark.parametrize(
    'component, hierarchy, expected, structure, asset_name',
    [
        (
            file_component,
            [],
            '{project_name}/my_new_asset/v001/foo.png',
            ftrack_api.structure.standard.StandardStructure(),
            'my_new_asset'
        ),
        (
            file_component,
            [],
            '{project_name}/foobar/my_new_asset/v001/foo.png',
            ftrack_api.structure.standard.StandardStructure(
                project_versions_prefix='foobar'
            ),
            'my_new_asset'
        ),
        (
            file_component,
            ['baz1', 'bar'],
            '{project_name}/baz1/bar/my_new_asset/v001/foo.png',
            ftrack_api.structure.standard.StandardStructure(),
            'my_new_asset'
        ),
        (
            sequence_component,
            ['baz2', 'bar'],
            '{project_name}/baz2/bar/my_new_asset/v001/baz.%04d.jpg',
            ftrack_api.structure.standard.StandardStructure(),
            'my_new_asset'
        ),
        (
            sequence_component['members'][3],
            ['baz3', 'bar'],
            '{project_name}/baz3/bar/my_new_asset/v001/baz.0004.jpg',
            ftrack_api.structure.standard.StandardStructure(),
            'my_new_asset'
        ),
        (
            container_component,
            ['baz4', 'bar'],
            '{project_name}/baz4/bar/my_new_asset/v001/container_component',
            ftrack_api.structure.standard.StandardStructure(),
            'my_new_asset'
        ),
        (
            new_file_component(container=container_component),
            ['baz5', 'bar'],
            (
                '{project_name}/baz5/bar/my_new_asset/v001/container_component/'
                'foo.png'
            ),
            ftrack_api.structure.standard.StandardStructure(),
            'my_new_asset'
        ),
        (
            file_component,
            [u'björn'],
            '{project_name}/bjorn/my_new_asset/v001/foo.png',
            ftrack_api.structure.standard.StandardStructure(),
            'my_new_asset'
        ),
        (
            file_component,
            [u'björn!'],
            '{project_name}/bjorn_/my_new_asset/v001/foo.png',
            ftrack_api.structure.standard.StandardStructure(),
            'my_new_asset'
        ),
        (
            new_file_component(name=u'fää'),
            [],
            '{project_name}/my_new_asset/v001/faa.png',
            ftrack_api.structure.standard.StandardStructure(),
            'my_new_asset'
        ),
        (
            new_file_component(name=u'fo/o'),
            [],
            '{project_name}/my_new_asset/v001/fo_o.png',
            ftrack_api.structure.standard.StandardStructure(),
            'my_new_asset'
        ),
        (
            file_component,
            [],
            '{project_name}/aao/v001/foo.png',
            ftrack_api.structure.standard.StandardStructure(),
            u'åäö'
        ),
        (
            file_component,
            [],
            '{project_name}/my_ne____w_asset/v001/foo.png',
            ftrack_api.structure.standard.StandardStructure(),
            u'my_ne!!!!w_asset'
        ),
        (
            file_component,
            [u'björn2'],
            u'{project_name}/björn2/my_new_asset/v001/foo.png',
            ftrack_api.structure.standard.StandardStructure(
                illegal_character_substitute=None
            ),
            'my_new_asset'
        ),
        (
            file_component,
            [u'bj!rn'],
            '{project_name}/bj^rn/my_new_asset/v001/foo.png',
            ftrack_api.structure.standard.StandardStructure(
                illegal_character_substitute='^'
            ),
            'my_new_asset'
        )
    ], ids=[
        'file_component_on_project',
        'file_component_on_project_with_prefix',
        'file_component_with_hierarchy',
        'sequence_component',
        'sequence_component_member',
        'container_component',
        'container_component_member',
        'slugify_non_ascii_hierarchy',
        'slugify_illegal_hierarchy',
        'slugify_non_ascii_component_name',
        'slugify_illegal_component_name',
        'slugify_non_ascii_asset_name',
        'slugify_illegal_asset_name',
        'slugify_none',
        'slugify_other_character'
    ]
)
def test_get_resource_identifier(
    component, hierarchy, expected, structure, asset_name, new_project
):
    '''Get resource identifier.'''
    session = component.session

    # Create structure, asset and version.
    context_id = new_project['id']
    for name in hierarchy:
        context_id = session.create('Folder', {
            'name': name,
            'project_id': new_project['id'],
            'parent_id': context_id
        })['id']

    asset = session.create(
        'Asset', {'name': asset_name, 'context_id': context_id}
    )
    version = session.create('AssetVersion', {'asset': asset})

    # Update component with version.
    if component['container']:
        component['container']['version'] = version
    else:
        component['version'] = version

    session.commit()

    assert structure.get_resource_identifier(component) == expected.format(
        project_name=new_project['name']
    )


def test_unsupported_entity(user):
    '''Fail to get resource identifier for unsupported entity.'''
    structure = ftrack_api.structure.standard.StandardStructure()
    with pytest.raises(NotImplementedError):
        structure.get_resource_identifier(user)


def test_component_without_version_relation(new_project):
    '''Get an identifer for component without a version relation.'''
    session = new_project.session

    asset = session.create(
        'Asset', {'name': 'foo', 'context_id': new_project['id']}
    )
    version = session.create('AssetVersion', {'asset': asset})

    session.commit()

    file_component = new_file_component()
    file_component['version_id'] = version['id']

    structure = ftrack_api.structure.standard.StandardStructure()
    structure.get_resource_identifier(file_component)


def test_component_without_committed_version_relation():
    '''Fail to get an identifer for component without a committed version.'''
    file_component = new_file_component()
    session = file_component.session
    version = session.create('AssetVersion', {})

    file_component['version'] = version

    structure = ftrack_api.structure.standard.StandardStructure()

    with pytest.raises(ftrack_api.exception.StructureError):
        structure.get_resource_identifier(file_component)


@pytest.mark.xfail(
    raises=ftrack_api.exception.ServerError, 
    reason='Due to user permission errors.'
)
def test_component_without_committed_asset_relation():
    '''Fail to get an identifer for component without a committed asset.'''
    file_component = new_file_component()
    session = file_component.session
    version = session.create('AssetVersion', {})

    file_component['version'] = version

    session.commit()

    structure = ftrack_api.structure.standard.StandardStructure()

    with pytest.raises(ftrack_api.exception.StructureError):
        structure.get_resource_identifier(file_component)
