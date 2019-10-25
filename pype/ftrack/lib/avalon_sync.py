import os
import re
import json
from pype.lib import get_avalon_database
from bson.objectid import ObjectId
import avalon
import avalon.api
from avalon import schema
from avalon.vendor import toml, jsonschema
from pypeapp import Logger, Anatomy, config

ValidationError = jsonschema.ValidationError

log = Logger().get_logger(__name__)


def get_ca_mongoid():
    # returns name of Custom attribute that stores mongo_id
    return 'avalon_mongo_id'


def import_to_avalon(
    session, entity, ft_project, av_project, custom_attributes
):
    database = get_avalon_database()
    project_name = ft_project['full_name']
    output = {}
    errors = []

    entity_type = entity.entity_type
    ent_path = "/".join([ent["name"] for ent in entity['link']])

    log.debug("{} [{}] - Processing".format(ent_path, entity_type))

    ca_mongoid = get_ca_mongoid()
    # Validate if entity has custom attribute avalon_mongo_id
    if ca_mongoid not in entity['custom_attributes']:
        msg = (
            'Custom attribute "{}" for "{}" is not created'
            ' or don\'t have set permissions for API'
        ).format(ca_mongoid, entity['name'])
        log.error(msg)
        errors.append({'Custom attribute error': msg})
        output['errors'] = errors
        return output

    # Validate if entity name match REGEX in schema
    avalon_check_name(entity)

    entity_type = entity.entity_type
    # Project ////////////////////////////////////////////////////////////////
    if entity_type in ['Project']:
        type = 'project'

        proj_config = get_project_config(entity)
        schema.validate(proj_config)

        av_project_code = None
        if av_project is not None and 'code' in av_project['data']:
            av_project_code = av_project['data']['code']
        ft_project_code = ft_project['name']

        if av_project is None:
            log.debug("{} - Creating project".format(project_name))
            item = {
                'schema': "avalon-core:project-2.0",
                'type': type,
                'name': project_name,
                'data': dict(),
                'config': proj_config,
                'parent': None,
            }
            schema.validate(item)

            database[project_name].insert_one(item)

            av_project = database[project_name].find_one(
                {'type': type}
            )

        elif (
            av_project['name'] != project_name or
            (
                av_project_code is not None and
                av_project_code != ft_project_code
            )
        ):
            msg = (
                'You can\'t change {0} "{1}" to "{2}"'
                ', avalon wouldn\'t work properly!'
                '\n{0} was changed back!'
            )
            if av_project['name'] != project_name:
                entity['full_name'] = av_project['name']
                errors.append(
                    {'Changed name error': msg.format(
                        'Project name', av_project['name'], project_name
                    )}
                )

            if (
                av_project_code is not None and
                av_project_code != ft_project_code
            ):
                log.warning((
                    "{0} - Project code"
                    " is different in Avalon (\"{1}\")"
                    " that in Ftrack (\"{2}\")!"
                    " Trying to change it back in Ftrack to \"{1}\"."
                ).format(
                    ent_path, str(av_project_code), str(ft_project_code)
                ))

                entity['name'] = av_project_code
                errors.append(
                    {'Changed name error': msg.format(
                        'Project code', av_project_code, ft_project_code
                    )}
                )

            try:
                session.commit()
                log.info((
                    "{} - Project code was changed back to \"{}\""
                ).format(ent_path, str(av_project_code)))
            except Exception:
                log.error(
                    (
                        "{} - Couldn't change project code back to \"{}\"."
                    ).format(ent_path, str(av_project_code)),
                    exc_info=True
                )

            output['errors'] = errors
            return output

        else:
            # not override existing templates!
            templates = av_project['config'].get('template', None)
            if templates is not None:
                for key, value in proj_config['template'].items():
                    if (
                        key in templates and
                        templates[key] is not None and
                        templates[key] != value
                    ):
                        proj_config['template'][key] = templates[key]

        projectId = av_project['_id']

        data = get_data(
            entity, session, custom_attributes
        )

        cur_data = av_project.get('data') or {}

        enter_data = {}
        for k, v in cur_data.items():
            enter_data[k] = v
        for k, v in data.items():
            enter_data[k] = v

        log.debug("{} - Updating data".format(ent_path))
        database[project_name].update_many(
            {'_id': ObjectId(projectId)},
            {'$set': {
                'name': project_name,
                'config': proj_config,
                'data': data
            }}
        )

        entity['custom_attributes'][ca_mongoid] = str(projectId)
        session.commit()

        output['project'] = av_project

        return output

    # Asset - /////////////////////////////////////////////////////////////
    if av_project is None:
        result = import_to_avalon(
            session, ft_project, ft_project, av_project, custom_attributes
        )

        if 'errors' in result:
            output['errors'] = result['errors']
            return output

        elif 'project' not in result:
            msg = 'During project import went something wrong'
            errors.append({'Unexpected error': msg})
            output['errors'] = errors
            return output

        av_project = result['project']
        output['project'] = result['project']

    projectId = av_project['_id']
    data = get_data(
        entity, session, custom_attributes
    )

    name = entity['name']

    avalon_asset = None
    # existence of this custom attr is already checked
    if ca_mongoid not in entity['custom_attributes']:
        msg = (
            "Entity type \"{}\" don't have created custom attribute \"{}\""
            " or user \"{}\" don't have permissions to read or change it."
        ).format(entity_type, ca_mongoid, session.api_user)

        log.error(msg)
        errors.append({'Missing Custom attribute': msg})
        output['errors'] = errors
        return output

    mongo_id = entity['custom_attributes'][ca_mongoid]
    mongo_id = mongo_id.replace(' ', '').replace('\n', '')
    try:
        ObjectId(mongo_id)
    except Exception:
        mongo_id = ''

    if mongo_id != '':
        avalon_asset = database[project_name].find_one(
            {'_id': ObjectId(mongo_id)}
        )

    if avalon_asset is None:
        avalon_asset = database[project_name].find_one(
            {'type': 'asset', 'name': name}
        )
        if avalon_asset is None:
            item = {
                'schema': "avalon-core:asset-3.0",
                'name': name,
                'parent': ObjectId(projectId),
                'type': 'asset',
                'data': data
            }
            schema.validate(item)
            mongo_id = database[project_name].insert_one(item).inserted_id
            log.debug("{} - Created in project \"{}\"".format(
                ent_path, project_name
            ))
        # Raise error if it seems to be different ent. with same name
        elif avalon_asset['data']['parents'] != data['parents']:
            msg = (
                "{} - In Avalon DB already exists entity with name \"{}\""
                "\n- \"{}\""
            ).format(ent_path, name, "/".join(db_asset_path_items))
            log.error(msg)
            errors.append({'Entity name duplication': msg})
            output['errors'] = errors
            return output

        # Store new ID (in case that asset was removed from DB)
        else:
            mongo_id = avalon_asset['_id']
    else:
        if avalon_asset['name'] != entity['name']:
            if changeability_check_childs(entity) is False:
                msg = (
                    '{} - You can\'t change name "{}" to "{}"'
                    ', avalon wouldn\'t work properly!'
                    '\n\nName was changed back!'
                    '\n\nCreate new entity if you want to change name.'
                ).format(ent_path, avalon_asset['name'], entity['name'])

                log.warning(msg)
                entity['name'] = avalon_asset['name']
                session.commit()
                errors.append({'Changed name error': msg})

        if avalon_asset['data']['parents'] != data['parents']:
            old_path = '/'.join(avalon_asset['data']['parents'])
            new_path = '/'.join(data['parents'])

            msg = (
                'You can\'t move with entities.'
                '\nEntity "{}" was moved from "{}" to "{}"'
                '\n\nAvalon won\'t work properly, {}!'
            )

            moved_back = False
            if 'visualParent' in avalon_asset['data']:
                asset_parent_id = avalon_asset['data']['visualParent'] or avalon_asset['parent']

                asset_parent = database[project_name].find_one(
                    {'_id': ObjectId(asset_parent_id)}
                )
                ft_parent_id = asset_parent['data']['ftrackId']
                try:
                    entity['parent_id'] = ft_parent_id
                    session.commit()
                    msg = msg.format(
                        avalon_asset['name'], old_path, new_path,
                        'entity was moved back'
                    )
                    log.warning(msg)
                    moved_back = True

                except Exception:
                    moved_back = False

            if moved_back is False:
                msg = msg.format(
                    avalon_asset['name'], old_path, new_path,
                    'please move it back'
                )
                log.error(msg)

            errors.append({'Hierarchy change error': msg})

    if len(errors) > 0:
        output['errors'] = errors
        return output

    avalon_asset = database[project_name].find_one(
        {'_id': ObjectId(mongo_id)}
    )

    cur_data = avalon_asset.get('data') or {}

    enter_data = {}
    for k, v in cur_data.items():
        enter_data[k] = v
    for k, v in data.items():
        enter_data[k] = v

    database[project_name].update_many(
        {'_id': ObjectId(mongo_id)},
        {'$set': {
            'name': name,
            'data': enter_data,
            'parent': ObjectId(projectId)
        }})
    log.debug("{} - Updated data (in project \"{}\")".format(
        ent_path, project_name
    ))
    entity['custom_attributes'][ca_mongoid] = str(mongo_id)
    session.commit()

    return output


def get_avalon_attr(session, split_hierarchical=False):
    custom_attributes = []
    hier_custom_attributes = []
    cust_attrs_query = (
        "select id, entity_type, object_type_id, is_hierarchical"
        " from CustomAttributeConfiguration"
        " where group.name = \"avalon\""
    )
    all_avalon_attr = session.query(cust_attrs_query).all()
    for cust_attr in all_avalon_attr:
        if 'avalon_' in cust_attr['key']:
            continue

        if split_hierarchical:
            if cust_attr["is_hierarchical"]:
                hier_custom_attributes.append(cust_attr)
                continue

        custom_attributes.append(cust_attr)

    if split_hierarchical:
        # return tuple
        return custom_attributes, hier_custom_attributes

    return custom_attributes


def changeability_check_childs(entity):
    if (entity.entity_type.lower() != 'task' and 'children' not in entity):
        return True
    childs = entity['children']
    for child in childs:
        if child.entity_type.lower() == 'task':
            available_statuses = config.get_presets().get(
                "ftrack", {}).get(
                "ftrack_config", {}).get(
                "sync_to_avalon", {}).get(
                "statuses_name_change", []
            )
            ent_status = child['status']['name'].lower()
            if ent_status not in available_statuses:
                return False
        # If not task go deeper
        elif changeability_check_childs(child) is False:
            return False
    # If everything is allright
    return True


def get_data(entity, session, custom_attributes):
    database = get_avalon_database()

    entity_type = entity.entity_type

    if entity_type.lower() == 'project':
        ft_project = entity
    elif entity_type.lower() != 'project':
        ft_project = entity['project']
        av_project = get_avalon_project(ft_project)

    project_name = ft_project['full_name']

    data = {}
    data['ftrackId'] = entity['id']
    data['entityType'] = entity_type

    ent_types_query = "select id, name from ObjectType"
    ent_types = session.query(ent_types_query).all()
    ent_types_by_name = {
        ent_type["name"]: ent_type["id"] for ent_type in ent_types
    }

    for cust_attr in custom_attributes:
        # skip hierarchical attributes
        if cust_attr.get('is_hierarchical', False):
            continue

        key = cust_attr['key']
        if cust_attr['entity_type'].lower() in ['asset']:
            data[key] = entity['custom_attributes'][key]

        elif (
            cust_attr['entity_type'].lower() in ['show'] and
            entity_type.lower() == 'project'
        ):
            data[key] = entity['custom_attributes'][key]

        elif (
            cust_attr['entity_type'].lower() in ['task'] and
            entity_type.lower() != 'project'
        ):
            # Put space between capitals (e.g. 'AssetBuild' -> 'Asset Build')
            entity_type_full = re.sub(r"(\w)([A-Z])", r"\1 \2", entity_type)
            # Get object id of entity type
            ent_obj_type_id = ent_types_by_name.get(entity_type_full)

            # Backup soluction when id is not found by prequeried objects
            if not ent_obj_type_id:
                query = 'ObjectType where name is "{}"'.format(
                    entity_type_full
                )
                ent_obj_type_id = session.query(query).one()['id']

            if cust_attr['object_type_id'] == ent_obj_type_id:
                if key in entity['custom_attributes']:
                    data[key] = entity['custom_attributes'][key]

    if entity_type in ['Project']:
        data['code'] = entity['name']
        return data

    # Get info for 'Data' in Avalon DB
    tasks = []
    for child in entity['children']:
        if child.entity_type in ['Task']:
            tasks.append(child['name'])

    # Get list of parents without project
    parents = []
    folderStruct = []
    for i in range(1, len(entity['link'])-1):
        parEnt = session.get(
            entity['link'][i]['type'],
            entity['link'][i]['id']
        )
        parName = parEnt['name']
        folderStruct.append(parName)
        parents.append(parEnt)

    parentId = None

    for parent in parents:
        parentId = database[project_name].find_one(
            {'type': 'asset', 'name': parName}
        )['_id']
        if parent['parent'].entity_type != 'project' and parentId is None:
            import_to_avalon(
                session, parent, ft_project, av_project, custom_attributes
            )
            parentId = database[project_name].find_one(
                {'type': 'asset', 'name': parName}
            )['_id']

    hierarchy = ""
    if len(folderStruct) > 0:
        hierarchy = os.path.sep.join(folderStruct)

    data['visualParent'] = parentId
    data['parents'] = folderStruct
    data['tasks'] = tasks
    data['hierarchy'] = hierarchy

    return data


def get_avalon_project(ft_project):
    database = get_avalon_database()
    project_name = ft_project['full_name']
    ca_mongoid = get_ca_mongoid()
    if ca_mongoid not in ft_project['custom_attributes']:
        return None

    # try to find by Id
    project_id = ft_project['custom_attributes'][ca_mongoid]
    try:
        avalon_project = database[project_name].find_one({
            '_id': ObjectId(project_id)
        })
    except Exception:
        avalon_project = None

    if avalon_project is None:
        avalon_project = database[project_name].find_one({
            'type': 'project'
        })

    return avalon_project


def get_avalon_project_template():
    """Get avalon template

    Returns:
        dictionary with templates
    """
    templates = Anatomy().templates
    return {
        'workfile': templates["avalon"]["workfile"],
        'work': templates["avalon"]["work"],
        'publish': templates["avalon"]["publish"]
    }


def get_project_config(entity):
    proj_config = {}
    proj_config['schema'] = 'avalon-core:config-1.0'
    proj_config['tasks'] = get_tasks(entity)
    proj_config['apps'] = get_project_apps(entity)
    proj_config['template'] = get_avalon_project_template()

    return proj_config


def get_tasks(project):
    task_types = project['project_schema']['_task_type_schema']['types']
    return [{'name': task_type['name']} for task_type in task_types]


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
            toml_path = avalon.lib.which_app(app)
            if not toml_path:
                log.warning((
                    'Missing config file for application "{}"'
                ).format(app))
                continue

            apps.append({
                'name': app,
                'label': toml.load(toml_path)['label']
            })

        except Exception as e:
            log.warning('Error with application {0} - {1}'.format(app, e))
    return apps


def avalon_check_name(entity, in_schema=None):
    default_pattern = "^[a-zA-Z0-9_.]*$"

    name = entity["name"]
    schema_name = "asset-3.0"

    if in_schema:
        schema_name = in_schema
    elif entity.entity_type.lower() == "project":
        name = entity["full_name"]
        schema_name = "project-2.0"

    schema_obj = avalon.schema._cache.get(schema_name + ".json")
    name_pattern = schema_obj.get("properties", {}).get("name", {}).get(
        "pattern", default_pattern
    )
    if not re.match(name_pattern, name):
        msg = "\"{}\" includes unsupported symbols like \"dash\" or \"space\""
        raise ValueError(msg.format(name))


def show_errors(obj, event, errors):
    title = 'Hey You! You raised few Errors! (*look below*)'
    items = []
    splitter = {'type': 'label', 'value': '---'}
    for error in errors:
        for key, message in error.items():
            error_title = {
                'type': 'label',
                'value': '# {}'.format(key)
            }
            error_message = {
                'type': 'label',
                'value': '<p>{}</p>'.format(message)
            }
            if len(items) > 0:
                items.append(splitter)
            items.append(error_title)
            items.append(error_message)
            obj.log.error(
                '{}: {}'.format(key, message)
            )
    obj.show_interface(items, title, event=event)
