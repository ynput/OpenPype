# fttrack help functions


# import ftrack
import os
from pprint import *


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
