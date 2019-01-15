import os
import re
from pype import lib
from avalon import io, inventory
from bson.objectid import ObjectId
from pype.ftrack.ftrack_utils import ftrack_utils
from avalon.vendor import jsonschema
from app.api import Logger
ValidationError = jsonschema.ValidationError

log = Logger.getLogger(__name__)


def get_ca_mongoid():
    # returns name of Custom attribute that stores mongo_id
    return 'avalon_mongo_id'


def import_to_avalon(
    session, entity, ft_project, av_project, custom_attributes
):
    output = {}
    errors = []

    ca_mongoid = get_ca_mongoid()
    # Validate if entity has custom attribute avalon_mongo_id
    if ca_mongoid not in entity['custom_attributes']:
        msg = (
            'Custom attribute "{}" for "{}" is not created'
            ' or don\'t have set permissions for API'
        ).format(ca_mongoid, entity['name'])
        errors.append({'Custom attribute error': msg})
        output['errors'] = errors
        return output

    # Validate if entity name match REGEX in schema
    try:
        ftrack_utils.avalon_check_name(entity)
    except ValidationError:
        msg = '"{}" includes unsupported symbols like "dash" or "space"'
        errors.append({'Unsupported character': msg})
        output['errors'] = errors
        return output

    entity_type = entity.entity_type
    # Project ////////////////////////////////////////////////////////////////
    if entity_type in ['Project']:
        type = 'project'
        name = entity['full_name']
        config = ftrack_utils.get_config(entity)
        template = lib.get_avalon_project_template_schema()

        av_project_code = None
        if av_project is not None and 'code' in av_project['data']:
            av_project_code = av_project['data']['code']
        ft_project_code = ft_project['name']

        if av_project is None:
            inventory.save(name, config, template)
            av_project = io.find_one({'type': type, 'name': name})

        elif av_project['name'] != name or av_project_code != ft_project_code:
            msg = (
                'You can\'t change {0} "{1}" to "{2}"'
                ', avalon wouldn\'t work properly!'
                '\n{0} was changed back!'
            )
            if av_project['name'] != name:
                entity['full_name'] = av_project['name']
                errors.append(
                    {'Changed name error': msg.format(
                        'Project name', av_project['name'], name
                    )}
                )
            if av_project_code != ft_project_code:
                entity['name'] = av_project_code
                errors.append(
                    {'Changed name error': msg.format(
                        'Project code', av_project_code, ft_project_code
                    )}
                )

            session.commit()

            output['errors'] = errors
            return output

        projectId = av_project['_id']

        data = get_data(
            entity, session, custom_attributes
        )

        io.update_many(
            {'_id': ObjectId(projectId)},
            {'$set': {
                'name': name,
                'config': config,
                'data': data,
            }})

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

    # 1. hierarchical entity have silo set to None
    silo = None
    if len(data['parents']) > 0:
        silo = data['parents'][0]

    name = entity['name']

    os.environ['AVALON_SILO'] = silo
    os.environ['AVALON_ASSET'] = name

    avalon_asset = None
    # existence of this custom attr is already checked
    if ca_mongoid not in entity['custom_attributes']:
        msg = '"{}" don\'t have "{}" custom attribute'
        errors.append({'Missing Custom attribute': msg.format(
            entity_type, ca_mongoid
        )})
        output['errors'] = errors
        return output

    mongo_id = entity['custom_attributes'][ca_mongoid]

    if mongo_id is not '':
        avalon_asset = io.find_one({'_id': ObjectId(mongo_id)})

    if avalon_asset is None:
        avalon_asset = io.find_one({'type': 'asset', 'name': name})
        if avalon_asset is None:
            mongo_id = inventory.create_asset(
                name, silo, data, ObjectId(projectId)
            )
        # Raise error if it seems to be different ent. with same name
        elif (
            avalon_asset['data']['parents'] != data['parents'] or
            avalon_asset['silo'] != silo
        ):
            msg = (
                'In Avalon DB already exists entity with name "{0}"'
            ).format(name)
            errors.append({'Entity name duplication': msg})
            output['errors'] = errors
            return output
    else:
        if avalon_asset['name'] != entity['name']:
            if silo is None or changeability_check_childs(entity) is False:
                msg = (
                    'You can\'t change name {} to {}'
                    ', avalon wouldn\'t work properly!'
                    '\n\nName was changed back!'
                    '\n\nCreate new entity if you want to change name.'
                ).format(avalon_asset['name'], entity['name'])
                entity['name'] = avalon_asset['name']
                session.commit()
                errors.append({'Changed name error': msg})

        if (
            avalon_asset['silo'] != silo or
            avalon_asset['data']['parents'] != data['parents']
        ):
            old_path = '/'.join(avalon_asset['data']['parents'])
            new_path = '/'.join(data['parents'])

            msg = (
                'You can\'t move with entities.'
                '\nEntity "{}" was moved from "{}" to "{}"'
                '\n\nAvalon won\'t work properly, {}!'
            )

            moved_back = False
            if 'visualParent' in avalon_asset['data']:
                if silo is None:
                    asset_parent_id = avalon_asset['parent']
                else:
                    asset_parent_id = avalon_asset['data']['visualParent']

                asset_parent = io.find_one({'_id': ObjectId(asset_parent_id)})
                ft_parent_id = asset_parent['data']['ftrackId']
                try:
                    entity['parent_id'] = ft_parent_id
                    session.commit()
                    msg = msg.format(
                        avalon_asset['name'], old_path, new_path,
                        'entity was moved back'
                    )
                    moved_back = True

                except Exception:
                    moved_back = False

            if moved_back is False:
                msg = msg.format(
                    avalon_asset['name'], old_path, new_path,
                    'please move it back'
                )

            errors.append({'Hierarchy change error': msg})

    if len(errors) > 0:
        output['errors'] = errors
        return output

    io.update_many(
        {'_id': ObjectId(mongo_id)},
        {'$set': {
            'name': name,
            'silo': silo,
            'data': data,
            'parent': ObjectId(projectId)
        }})

    entity['custom_attributes'][ca_mongoid] = str(mongo_id)
    session.commit()

    return output


def get_avalon_attr(session):
    custom_attributes = []
    query = 'CustomAttributeGroup where name is "avalon"'
    all_avalon_attr = session.query(query).one()
    for cust_attr in all_avalon_attr['custom_attribute_configurations']:
        if 'avalon_' not in cust_attr['key']:
            custom_attributes.append(cust_attr)
    return custom_attributes


def changeability_check_childs(entity):
        if (entity.entity_type.lower() != 'task' and 'children' not in entity):
            return True
        childs = entity['children']
        for child in childs:
            if child.entity_type.lower() == 'task':
                config = ftrack_utils.get_config_data()
                if 'sync_to_avalon' in config:
                    config = config['sync_to_avalon']
                if 'statuses_name_change' in config:
                    available_statuses = config['statuses_name_change']
                else:
                    available_statuses = []
                ent_status = child['status']['name'].lower()
                if ent_status not in available_statuses:
                    return False
            # If not task go deeper
            elif changeability_check_childs(child) is False:
                return False
        # If everything is allright
        return True


def get_data(entity, session, custom_attributes):
    entity_type = entity.entity_type

    data = {}
    data['ftrackId'] = entity['id']
    data['entityType'] = entity_type

    for cust_attr in custom_attributes:
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
            query = 'ObjectType where name is "{}"'.format(entity_type_full)
            ent_obj_type_id = session.query(query).one()['id']

            if cust_attr['object_type_id'] == ent_obj_type_id:
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
        parentId = io.find_one({'type': 'asset', 'name': parName})['_id']
        if parent['parent'].entity_type != 'project' and parentId is None:
            parent.importToAvalon(session, parent)
            parentId = io.find_one({'type': 'asset', 'name': parName})['_id']

    hierarchy = os.path.sep.join(folderStruct)

    data['visualParent'] = parentId
    data['parents'] = folderStruct
    data['tasks'] = tasks
    data['hierarchy'] = hierarchy

    return data


def get_avalon_proj(ft_project):
    io.install()

    ca_mongoid = get_ca_mongoid()
    if ca_mongoid not in ft_project['custom_attributes']:
        return None

    project_id = ft_project['custom_attributes'][ca_mongoid]
    try:
        avalon_project = io.find_one({
            "_id": ObjectId(project_id)
        })
    except Exception:
        avalon_project = None

    if avalon_project is None:
        avalon_project = io.find_one({
            "type": "project",
            "name": ft_project["full_name"]
        })

    io.uninstall()

    return avalon_project
