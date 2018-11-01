import os
import operator
import ftrack_api
import collections
import sys
import json
import base64

# sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# from ftrack_kredenc.lucidity.vendor import yaml
# from ftrack_kredenc import lucidity
#
#
# def get_ftrack_connect_path():
#
#     ftrack_connect_root = os.path.abspath(os.getenv('FTRACK_CONNECT_PACKAGE'))
#
#     return ftrack_connect_root
#
#
# def from_yaml(filepath):
#     ''' Parse a Schema from a YAML file at the given *filepath*.
#     '''
#     with open(filepath, 'r') as f:
#         data = yaml.safe_load(f)
#     return data
#
#
# def get_task_enviro(entity, environment=None):
#
#     context = get_context(entity)
#
#     if not environment:
#         environment = {}
#
#     for key in context:
#         os.environ[key.upper()] = context[key]['name']
#         environment[key.upper()] = context[key]['name']
#
#         if key == 'Project':
#             os.putenv('PROJECT_ROOT', context[key]['root'])
#             os.environ['PROJECT_ROOT'] = context[key]['root']
#             environment['PROJECT_ROOT'] = context[key]['root']
#             print('PROJECT_ROOT: ' + context[key]['root'])
#         print(key + ': ' + context[key]['name'])
#
#     return environment
#
#
# def get_entity():
#     decodedEventData = json.loads(
#         base64.b64decode(
#             os.environ.get('FTRACK_CONNECT_EVENT')
#         )
#     )
#
#     entity = decodedEventData.get('selection')[0]
#
#     if entity['entityType'] == 'task':
#         return ftrack_api.Task(entity['entityId'])
#     else:
#         return None
#
#
# def set_env_vars():
#
#     entity = get_entity()
#
#     if entity:
#         if not os.environ.get('project_root'):
#             enviro = get_task_enviro(entity)
#
#             print(enviro)
#
#
def get_context(entity):

    entityName = entity['name']
    entityId = entity['id']
    entityType = entity.entity_type
    entityDescription = entity['description']

    print(100*"*")
    for k in entity['ancestors']:
        print(k['name'])
    print(100*"*")
    hierarchy = entity.getParents()

    ctx = collections.OrderedDict()

    if entity.get('entityType') == 'task' and entityType == 'Task':
        taskType = entity.getType().getName()
        entityDic = {
            'type': taskType,
            'name': entityName,
            'id': entityId,
            'description': entityDescription
        }
    elif entity.get('entityType') == 'task':
        entityDic = {
            'name': entityName,
            'id': entityId,
            'description': entityDescription
        }

    ctx[entityType] = entityDic

    folder_counter = 0

    for ancestor in hierarchy:
        tempdic = {}
        if isinstance(ancestor, ftrack_api.Component):
            # Ignore intermediate components.
            continue

        tempdic['name'] = ancestor.getName()
        tempdic['id'] = ancestor.getId()

        try:
            objectType = ancestor.getObjectType()
            tempdic['description'] = ancestor.getDescription()
        except AttributeError:
            objectType = 'Project'
            tempdic['description'] = ''

        if objectType == 'Asset Build':
            tempdic['type'] = ancestor.getType().get('name')
            objectType = objectType.replace(' ', '_')
        elif objectType == 'Project':
            tempdic['code'] = tempdic['name']
            tempdic['name'] = ancestor.get('fullname')
            tempdic['root'] = ancestor.getRoot()

        if objectType == 'Folder':
            objectType = objectType + str(folder_counter)
            folder_counter += 1
        ctx[objectType] = tempdic

    return ctx


def getNewContext(entity):

    parents = []
    item = entity
    while True:
        item = item['parent']
        if not item:
            break
        parents.append(item)

    ctx = collections.OrderedDict()

    entityDic = {
        'name': entity['name'],
        'id': entity['id'],
    }
    try:
        entityDic['type'] = entity['type']['name']
    except:
        pass

    ctx[entity['object_type']['name']] = entityDic

    print(100*"-")
    for p in parents:
        print(p)
    # add all parents to the context
    for parent in parents:
        tempdic = {}
        if not parent.get('project_schema'):
            tempdic = {
                'name': parent['full_name'],
                'code': parent['name'],
                'id': parent['id'],
            }
            tempdic = {
                'name': parent['name'],
                'id': parent['id'],
            }
            object_type = parent['object_type']['name']

        ctx[object_type] = tempdic

    # add project to the context
    project = entity['project']
    ctx['Project'] = {
        'name': project['full_name'],
        'code': project['name'],
        'id': project['id'],
        'root': project['root'],
    },

    return ctx
#
#
# def get_frame_range():
#
#     entity = get_entity()
#     entityType = entity.getObjectType()
#     environment = {}
#
#     if entityType == 'Task':
#         try:
#             environment['FS'] = str(int(entity.getFrameStart()))
#         except Exception:
#             environment['FS'] = '1'
#         try:
#             environment['FE'] = str(int(entity.getFrameEnd()))
#         except Exception:
#             environment['FE'] = '1'
#     else:
#         try:
#             environment['FS'] = str(int(entity.getFrameStart()))
#         except Exception:
#             environment['FS'] = '1'
#         try:
#             environment['FE'] = str(int(entity.getFrameEnd()))
#         except Exception:
#             environment['FE'] = '1'
#
#
# def get_asset_name_by_id(id):
#     for t in ftrack_api.getAssetTypes():
#         try:
#             if t.get('typeid') == id:
#                 return t.get('name')
#         except:
#             return None
#
#
# def get_status_by_name(name):
#     statuses = ftrack_api.getTaskStatuses()
#
#     result = None
#     for s in statuses:
#         if s.get('name').lower() == name.lower():
#             result = s
#
#     return result
#
#
# def sort_types(types):
#     data = {}
#     for t in types:
#         data[t] = t.get('sort')
#
#     data = sorted(data.items(), key=operator.itemgetter(1))
#     results = []
#     for item in data:
#         results.append(item[0])
#
#     return results
#
#
# def get_next_task(task):
#     shot = task.getParent()
#     tasks = shot.getTasks()
#
#     types_sorted = sort_types(ftrack_api.getTaskTypes())
#
#     next_types = None
#     for t in types_sorted:
#         if t.get('typeid') == task.get('typeid'):
#             try:
#                 next_types = types_sorted[(types_sorted.index(t) + 1):]
#             except:
#                 pass
#
#     for nt in next_types:
#         for t in tasks:
#             if nt.get('typeid') == t.get('typeid'):
#                 return t
#
#     return None
#
#
# def get_latest_version(versions):
#     latestVersion = None
#     if len(versions) > 0:
#         versionNumber = 0
#         for item in versions:
#             if item.get('version') > versionNumber:
#                 versionNumber = item.getVersion()
#                 latestVersion = item
#     return latestVersion
#
#
# def get_thumbnail_recursive(task):
#     if task.get('thumbid'):
#         thumbid = task.get('thumbid')
#         return ftrack_api.Attachment(id=thumbid)
#     if not task.get('thumbid'):
#         parent = ftrack_api.Task(id=task.get('parent_id'))
#         return get_thumbnail_recursive(parent)
#
#
# # paths_collected
#
# def getFolderHierarchy(context):
#         '''Return structure for *hierarchy*.
#         '''
#
#         hierarchy = []
#         for key in reversed(context):
#             hierarchy.append(context[key]['name'])
#             print(hierarchy)
#
#         return os.path.join(*hierarchy[1:-1])
#
#
def tweakContext(context, include=False):

    for key in context:
        if key == 'Asset Build':
            context['Asset_Build'] = context.pop(key)
            key = 'Asset_Build'
        description = context[key].get('description')
        if description:
            context[key]['description'] = '_' + description

    hierarchy = []
    for key in reversed(context):
        hierarchy.append(context[key]['name'])

    if include:
        hierarchy = os.path.join(*hierarchy[1:])
    else:
        hierarchy = os.path.join(*hierarchy[1:-1])

    context['ft_hierarchy'] = hierarchy


def getSchema(entity):

    project = entity['project']
    schema = project['project_schema']['name']

    tools = os.path.abspath(os.environ.get('studio_tools'))

    schema_path = os.path.join(tools, 'studio', 'templates', (schema + '_' + project['name'] + '.yml'))
    if not os.path.exists(schema_path):
        schema_path = os.path.join(tools, 'studio', 'templates', (schema + '.yml'))
    if not os.path.exists(schema_path):
        schema_path = os.path.join(tools, 'studio', 'templates', 'default.yml')

    schema = lucidity.Schema.from_yaml(schema_path)

    print(schema_path)
    return schema


# def getAllPathsYaml(entity, root=''):
#
#     if isinstance(entity, str) or isinstance(entity, unicode):
#         entity = ftrack_api.Task(entity)
#
#     context = get_context(entity)
#
#     tweakContext(context)
#
#     schema = getSchema(entity)
#
#     paths = schema.format_all(context)
#     paths_collected = []
#
#     for path in paths:
#         tweak_path = path[0].replace(" ", '_').replace('\'', '').replace('\\', '/')
#
#         tempPath = os.path.join(root, tweak_path)
#         path = list(path)
#         path[0] = tempPath
#         paths_collected.append(path)
#
#     return paths_collected
#

def getPathsYaml(entity, templateList=None, root=None, **kwargs):
    '''
    version=None
    ext=None
    item=None
    family=None
    subset=None
    '''

    context = get_context(entity)

    if entity.entity_type != 'Task':
        tweakContext(context, include=True)
    else:
        tweakContext(context)

    context.update(kwargs)

    host = sys.executable.lower()

    ext = None
    if not context.get('ext'):
        if "nuke" in host:
            ext = 'nk'
        elif "maya" in host:
            ext = 'ma'
        elif "houdini" in host:
            ext = 'hip'
        if ext:
            context['ext'] = ext

    if not context.get('subset'):
        context['subset'] = ''
    else:
        context['subset'] = '_' + context['subset']

    schema = getSchema(entity)
    paths = schema.format_all(context)
    paths_collected = set([])
    for temp_mask in templateList:
        for path in paths:
            if temp_mask in path[1].name:
                path = path[0].lower().replace(" ", '_').replace('\'', '').replace('\\', '/')
                path_list = path.split('/')
                if path_list[0].endswith(':'):
                    path_list[0] = path_list[0] + os.path.sep
                path = os.path.join(*path_list)
                temppath = os.path.join(root, path)
                paths_collected.add(temppath)

    return list(paths_collected)
