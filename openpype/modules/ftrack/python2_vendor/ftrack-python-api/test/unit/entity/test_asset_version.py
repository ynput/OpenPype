# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack
import json


def test_create_component(new_asset_version, temporary_file):
    '''Create component on asset version.'''
    session = new_asset_version.session
    component = new_asset_version.create_component(
        temporary_file, location=None
    )
    assert component['version'] is new_asset_version

    # Have to delete component before can delete asset version.
    session.delete(component)


def test_create_component_specifying_different_version(
    new_asset_version, temporary_file
):
    '''Create component on asset version ignoring specified version.'''
    session = new_asset_version.session
    component = new_asset_version.create_component(
        temporary_file, location=None,
        data=dict(
            version_id='this-value-should-be-ignored',
            version='this-value-should-be-overridden'
        )
    )
    assert component['version'] is new_asset_version

    # Have to delete component before can delete asset version.
    session.delete(component)


def test_encode_media(new_asset_version, video_path):
    '''Encode media based on a file path

    Encoded components should be associated with the version.
    '''
    session = new_asset_version.session
    job = new_asset_version.encode_media(video_path)
    assert job.entity_type == 'Job'

    job_data = json.loads(job['data'])
    assert 'output' in job_data
    assert len(job_data['output'])
    assert 'component_id' in job_data['output'][0]

    component_id = job_data['output'][0]['component_id']
    component = session.get('FileComponent', component_id) 

    # Component should be associated with the version.
    assert component['version_id'] == new_asset_version['id']
