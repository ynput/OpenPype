import os
import json

import avalon
import avalon.api
from avalon.vendor import toml, jsonschema
from app.api import Logger
from pype import lib

log = Logger.getLogger(__name__)


def get_presets_path():
    templates = os.environ['PYPE_STUDIO_TEMPLATES']
    path_items = [templates, 'presets']
    filepath = os.path.sep.join(path_items)
    return filepath


def get_config_data():
    path_items = [get_presets_path(), 'ftrack', 'ftrack_config.json']
    filepath = os.path.sep.join(path_items)
    data = dict()
    try:
        with open(filepath) as data_file:
            data = json.load(data_file)

    except Exception as e:
        msg = (
            'Loading "Ftrack Config file" Failed.'
            ' Please check log for more information.'
            ' Times are set to default.'
        )
        log.warning("{} - {}".format(msg, str(e)))

    return data


def avalon_check_name(entity, inSchema=None):
    ValidationError = jsonschema.ValidationError
    alright = True
    name = entity['name']
    if " " in name:
        alright = False

    data = {}
    data['data'] = {}
    data['type'] = 'asset'
    schema = "avalon-core:asset-2.0"
    # TODO have project any REGEX check?
    if entity.entity_type in ['Project']:
        # data['type'] = 'project'
        name = entity['full_name']
        # schema = get_avalon_project_template_schema()
    # elif entity.entity_type in ['AssetBuild','Library']:
        # data['silo'] = 'Assets'
    # else:
    #     data['silo'] = 'Film'
    data['silo'] = 'Film'

    if inSchema is not None:
        schema = inSchema
    data['schema'] = schema
    data['name'] = name
    try:
        avalon.schema.validate(data)
    except ValidationError:
        alright = False

    if alright is False:
        msg = '"{}" includes unsupported symbols like "dash" or "space"'
        raise ValueError(msg.format(name))


def get_project_apps(entity):
    """ Get apps from project
    Requirements:
        'Entity' MUST be object of ftrack entity with entity_type 'Project'
    Checking if app from ftrack is available in Templates/bin/{app_name}.toml

    Returns:
        Array with dictionaries with app Name and Label
    """
    apps = []
    for app in entity['custom_attributes']['applications']:
        try:
            app_config = {}
            app_config['name'] = app
            app_config['label'] = toml.load(avalon.lib.which_app(app))['label']

            apps.append(app_config)

        except Exception as e:
            log.warning('Error with application {0} - {1}'.format(app, e))
    return apps


def get_project_config(entity):
    config = {}
    config['schema'] = lib.get_avalon_project_config_schema()
    config['tasks'] = [{'name': ''}]
    config['apps'] = get_project_apps(entity)
    config['template'] = lib.get_avalon_project_template()

    return config
