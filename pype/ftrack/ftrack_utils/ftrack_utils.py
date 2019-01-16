import os
import json

from pype import lib
import avalon
import avalon.api
from avalon.vendor import toml, jsonschema
from app.api import Logger

log = Logger.getLogger(__name__)


def get_config_data():
    templates = os.environ['PYPE_STUDIO_TEMPLATES']
    path_items = [templates, 'presets', 'ftrack', 'ftrack_config.json']
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


def get_apps(entity):
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


def get_config(entity):
    config = {}
    config['schema'] = lib.get_avalon_project_config_schema()
    config['tasks'] = [{'name': ''}]
    config['apps'] = get_apps(entity)
    config['template'] = lib.get_avalon_project_template()

    return config


def get_context(entity):
    parents = []
    item = entity
    while True:
        item = item['parent']
        if not item:
            break
        parents.append(item)

    ctx = collections.OrderedDict()
    folder_counter = 0

    entityDic = {
        'name': entity['name'],
        'id': entity['id'],
    }
    try:
        entityDic['type'] = entity['type']['name']
    except Exception:
        pass

    ctx[entity['object_type']['name']] = entityDic

    # add all parents to the context
    for parent in parents:
        tempdic = {}
        if not parent.get('project_schema'):
            tempdic = {
                'name': parent['name'],
                'id': parent['id'],
            }
            object_type = parent['object_type']['name']

            if object_type == 'Folder':
                object_type = object_type + str(folder_counter)
                folder_counter += 1

            ctx[object_type] = tempdic

    # add project to the context
    project = entity['project']
    ctx['Project'] = {
        'name': project['full_name'],
        'code': project['name'],
        'id': project['id'],
        'root': project['root']
    }

    return ctx


def get_status_by_name(name):
    statuses = ftrack.getTaskStatuses()

    result = None
    for s in statuses:
        if s.get('name').lower() == name.lower():
            result = s

    return result


def sort_types(types):
    data = {}
    for t in types:
        data[t] = t.get('sort')

    data = sorted(data.items(), key=operator.itemgetter(1))
    results = []
    for item in data:
        results.append(item[0])

    return results


def get_next_task(task):
    shot = task.getParent()
    tasks = shot.getTasks()

    types_sorted = sort_types(ftrack.getTaskTypes())

    next_types = None
    for t in types_sorted:
        if t.get('typeid') == task.get('typeid'):
            try:
                next_types = types_sorted[(types_sorted.index(t) + 1):]
            except Exception:
                pass

    for nt in next_types:
        for t in tasks:
            if nt.get('typeid') == t.get('typeid'):
                return t

    return None


def get_latest_version(versions):
    latestVersion = None
    if len(versions) > 0:
        versionNumber = 0
        for item in versions:
            if item.get('version') > versionNumber:
                versionNumber = item.getVersion()
                latestVersion = item
    return latestVersion


def get_thumbnail_recursive(task):
    if task.get('thumbid'):
        thumbid = task.get('thumbid')
        return ftrack.Attachment(id=thumbid)
    if not task.get('thumbid'):
        parent = ftrack.Task(id=task.get('parent_id'))
        return get_thumbnail_recursive(parent)
