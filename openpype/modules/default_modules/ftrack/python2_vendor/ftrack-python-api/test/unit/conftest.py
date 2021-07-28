# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import uuid
import tempfile
import shutil
import os

import pytest
import clique

import ftrack_api
import ftrack_api.symbol


def pytest_generate_tests(metafunc):
    '''Parametrize tests dynamically.

    If a test function has a corresponding parametrize function then call it
    passing along the *metafunc*. For example, for a "test_foo" function, look
    for and call "parametrize_test_foo" if it exists.

    This is useful when more complex dynamic parametrization is needed than the
    standard pytest.mark.parametrize decorator can provide.

    '''
    generator_name = 'parametrize_{}'.format(metafunc.function.__name__)
    generator = getattr(metafunc.module, generator_name, None)
    if callable(generator):
        generator(metafunc)


def _temporary_file(request, **kwargs):
    '''Return temporary file.'''
    file_handle, path = tempfile.mkstemp(**kwargs)
    os.close(file_handle)

    def cleanup():
        '''Remove temporary file.'''
        try:
            os.remove(path)
        except OSError:
            pass

    request.addfinalizer(cleanup)
    return path


@pytest.fixture()
def temporary_file(request):
    '''Return temporary file.'''
    return _temporary_file(request)


@pytest.fixture()
def temporary_image(request):
    '''Return temporary file.'''
    return _temporary_file(request, suffix='.jpg')


@pytest.fixture()
def temporary_directory(request):
    '''Return temporary directory.'''
    path = tempfile.mkdtemp()

    def cleanup():
        '''Remove temporary directory.'''
        shutil.rmtree(path)

    request.addfinalizer(cleanup)

    return path


@pytest.fixture()
def temporary_sequence(temporary_directory):
    '''Return temporary sequence of three files.

    Return the path using the `clique
    <http://clique.readthedocs.org/en/latest/>`_ format, for example::

        /tmp/asfjsfjoj3/%04d.jpg [1-3]

    '''
    items = []
    for index in range(3):
        item_path = os.path.join(
            temporary_directory, '{0:04d}.jpg'.format(index)
        )
        with open(item_path, 'w') as file_descriptor:
            file_descriptor.write(uuid.uuid4().hex)
            file_descriptor.close()

        items.append(item_path)

    collections, _ = clique.assemble(items)
    sequence_path = collections[0].format()

    return sequence_path


@pytest.fixture()
def video_path():
    '''Return a path to a video file.'''
    video = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            'fixture',
            'media',
            'colour_wheel.mov'
        )
    )

    return video


@pytest.fixture()
def session():
    '''Return session instance.'''
    return ftrack_api.Session()


@pytest.fixture()
def session_no_autoconnect_hub():
    '''Return session instance not auto connected to hub.'''
    return ftrack_api.Session(auto_connect_event_hub=False)


@pytest.fixture()
def unique_name():
    '''Return a unique name.'''
    return 'test-{0}'.format(uuid.uuid4())


@pytest.fixture()
def temporary_path(request):
    '''Return temporary path.'''
    path = tempfile.mkdtemp()

    def cleanup():
        '''Remove created path.'''
        try:
            shutil.rmtree(path)
        except OSError:
            pass

    request.addfinalizer(cleanup)

    return path


@pytest.fixture()
def new_user(request, session, unique_name):
    '''Return a newly created unique user.'''
    entity = session.create('User', {'username': unique_name})
    session.commit()

    def cleanup():
        '''Remove created entity.'''
        session.delete(entity)
        session.commit()

    request.addfinalizer(cleanup)

    return entity


@pytest.fixture()
def user(session):
    '''Return the same user entity for entire session.'''
    # Jenkins user
    entity = session.get('User', 'd07ae5d0-66e1-11e1-b5e9-f23c91df25eb')
    assert entity is not None

    return entity


@pytest.fixture()
def project_schema(session):
    '''Return project schema.'''
    # VFX Scheme
    entity = session.get(
        'ProjectSchema', '69cb7f92-4dbf-11e1-9902-f23c91df25eb'
    )
    assert entity is not None
    return entity


@pytest.fixture()
def new_project_tree(request, session, user):
    '''Return new project with basic tree.'''
    project_schema = session.query('ProjectSchema').first()
    default_shot_status = project_schema.get_statuses('Shot')[0]
    default_task_type = project_schema.get_types('Task')[0]
    default_task_status = project_schema.get_statuses(
        'Task', default_task_type['id']
    )[0]

    project_name = 'python_api_test_{0}'.format(uuid.uuid1().hex)
    project = session.create('Project', {
        'name': project_name,
        'full_name': project_name + '_full',
        'project_schema': project_schema
    })

    for sequence_number in range(1):
        sequence = session.create('Sequence', {
            'name': 'sequence_{0:03d}'.format(sequence_number),
            'parent': project
        })

        for shot_number in range(1):
            shot = session.create('Shot', {
                'name': 'shot_{0:03d}'.format(shot_number * 10),
                'parent': sequence,
                'status': default_shot_status
            })

            for task_number in range(1):
                task = session.create('Task', {
                    'name': 'task_{0:03d}'.format(task_number),
                    'parent': shot,
                    'status': default_task_status,
                    'type': default_task_type
                })

                session.create('Appointment', {
                    'type': 'assignment',
                    'context': task,
                    'resource': user
                })

    session.commit()

    def cleanup():
        '''Remove created entity.'''
        session.delete(project)
        session.commit()

    request.addfinalizer(cleanup)

    return project


@pytest.fixture()
def new_project(request, session, user):
    '''Return new empty project.'''
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


@pytest.fixture()
def project(session):
    '''Return same project for entire session.'''
    # Test project.
    entity = session.get('Project', '5671dcb0-66de-11e1-8e6e-f23c91df25eb')
    assert entity is not None

    return entity


@pytest.fixture()
def new_task(request, session, unique_name):
    '''Return a new task.'''
    project = session.query(
        'Project where id is 5671dcb0-66de-11e1-8e6e-f23c91df25eb'
    ).one()
    project_schema = project['project_schema']
    default_task_type = project_schema.get_types('Task')[0]
    default_task_status = project_schema.get_statuses(
        'Task', default_task_type['id']
    )[0]

    task = session.create('Task', {
        'name': unique_name,
        'parent': project,
        'status': default_task_status,
        'type': default_task_type
    })

    session.commit()

    def cleanup():
        '''Remove created entity.'''
        session.delete(task)
        session.commit()

    request.addfinalizer(cleanup)

    return task


@pytest.fixture()
def task(session):
    '''Return same task for entire session.'''
    # Tests/python_api/tasks/t1
    entity = session.get('Task', 'adb4ad6c-7679-11e2-8df2-f23c91df25eb')
    assert entity is not None

    return entity


@pytest.fixture()
def new_scope(request, session, unique_name):
    '''Return a new scope.'''
    scope = session.create('Scope', {
        'name': unique_name
    })

    session.commit()

    def cleanup():
        '''Remove created entity.'''
        session.delete(scope)
        session.commit()

    request.addfinalizer(cleanup)

    return scope


@pytest.fixture()
def new_job(request, session, unique_name, user):
    '''Return a new scope.'''
    job = session.create('Job', {
        'type': 'api_job',
        'user': user
    })

    session.commit()

    def cleanup():
        '''Remove created entity.'''
        session.delete(job)
        session.commit()

    request.addfinalizer(cleanup)

    return job


@pytest.fixture()
def new_note(request, session, unique_name, new_task, user):
    '''Return a new note attached to a task.'''
    note = new_task.create_note(unique_name, user)
    session.commit()

    def cleanup():
        '''Remove created entity.'''
        session.delete(note)
        session.commit()

    request.addfinalizer(cleanup)

    return note


@pytest.fixture()
def new_asset_version(request, session):
    '''Return a new asset version.'''
    asset_version = session.create('AssetVersion', {
        'asset_id': 'dd9a7e2e-c5eb-11e1-9885-f23c91df25eb'
    })
    session.commit()

    # Do not cleanup the version as that will sometimes result in a deadlock
    # database error.

    return asset_version


@pytest.fixture()
def new_component(request, session, temporary_file):
    '''Return a new component not in any location except origin.'''
    component = session.create_component(temporary_file, location=None)
    session.commit()

    def cleanup():
        '''Remove created entity.'''
        session.delete(component)
        session.commit()

    request.addfinalizer(cleanup)

    return component


@pytest.fixture()
def new_container_component(request, session, temporary_directory):
    '''Return a new container component not in any location except origin.'''
    component = session.create('ContainerComponent')

    # Add to special origin location so that it is possible to add to other
    # locations.
    origin_location = session.get(
        'Location', ftrack_api.symbol.ORIGIN_LOCATION_ID
    )
    origin_location.add_component(
        component, temporary_directory, recursive=False
    )

    session.commit()

    def cleanup():
        '''Remove created entity.'''
        session.delete(component)
        session.commit()

    request.addfinalizer(cleanup)

    return component


@pytest.fixture()
def new_sequence_component(request, session, temporary_sequence):
    '''Return a new sequence component not in any location except origin.'''
    component = session.create_component(temporary_sequence, location=None)
    session.commit()

    def cleanup():
        '''Remove created entity.'''
        session.delete(component)
        session.commit()

    request.addfinalizer(cleanup)

    return component


@pytest.fixture
def mocked_schemas():
    '''Return a list of mocked schemas.'''
    return [{
        'id': 'Foo',
        'type': 'object',
        'properties': {
            'id': {
                'type': 'string'
            },
            'string': {
                'type': 'string'
            },
            'integer': {
                'type': 'integer'
            },
            'number': {
                'type': 'number'
            },
            'boolean': {
                'type': 'boolean'
            },
            'bars': {
                'type': 'array',
                'items': {
                    'ref': '$Bar'
                }
            },
            'date': {
                'type': 'string',
                'format': 'date-time'
            }
        },
        'immutable': [
            'id'
        ],
        'primary_key': [
            'id'
        ],
        'required': [
            'id'
        ],
        'default_projections': [
            'id'
        ]
    }, {
        'id': 'Bar',
        'type': 'object',
        'properties': {
            'id': {
                'type': 'string'
            },
            'name': {
                'type': 'string'
            },
            'computed_value': {
                'type': 'string',
            }
        },
        'computed': [
            'computed_value'
        ],
        'immutable': [
            'id'
        ],
        'primary_key': [
            'id'
        ],
        'required': [
            'id'
        ],
        'default_projections': [
            'id'
        ]
    }]


@pytest.yield_fixture
def mocked_schema_session(mocker, mocked_schemas):
    '''Return a session instance with mocked schemas.'''
    with mocker.patch.object(
        ftrack_api.Session,
        '_load_schemas',
        return_value=mocked_schemas
    ):
        # Mock _configure_locations since it will fail if no location schemas
        # exist.
        with mocker.patch.object(
            ftrack_api.Session,
            '_configure_locations'
        ):
            patched_session = ftrack_api.Session()
            yield patched_session
