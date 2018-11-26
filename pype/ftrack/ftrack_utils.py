# fttrack help functions

import ftrack_api
import os
import traceback
from pprint import *
from pype import lib

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
            label = toml.load(lib.which_app(app))['label']
            apps.append({'name':app, 'label':label})
        except Exception as e:
            print('Error with application {0} - {1}'.format(app, e))
    return apps

def get_config(self, entity):
    config = {}
    config['schema'] = lib.get_avalon_project_config_schema()
    config['tasks'] = [{'name': ''}]
    config['apps'] = get_apps(entity)
    config['template'] = lib.get_avalon_project_template()

    return config

def checkRegex():
    # _handle_result -> would be solution?
    # """ TODO Check if name of entities match REGEX"""
    for entity in importable:
        for e in entity['link']:
            item = {
                "silo": "silo",
                "parent": "parent",
                "type": "asset",
                "schema": "avalon-core:asset-2.0",
                "name": e['name'],
                "data": dict(),
            }
            try:
                schema.validate(item)
            except Exception as e:
                print(e)
    print(e['name'])
    ftrack.EVENT_HUB.publishReply(
        event,
        data={
            'success': False,
            'message': 'Entity name contains invalid character!'
        }
    )


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
    except:
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
            except:
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
