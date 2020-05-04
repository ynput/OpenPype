import os
import json
import arrow
import ftrack_api
from pype.ftrack import BaseAction
from pype.ftrack.lib.avalon_sync import CustAttrIdKey
from pypeapp import config

"""
This action creates/updates custom attributes.
- first part take care about avalon_mongo_id attribute
- second part is based on json file in templates:
    ~/PYPE-TEMPLATES/presets/ftrack/ftrack_custom_attributes.json
    - you can add Custom attributes based on these conditions

*** Required ***************************************************************

label (string)
  - label that will show in ftrack

key (string)
  - must contain only chars [a-z0-9_]

type (string)
  - type of custom attribute
  - possibilities: text, boolean, date, enumerator, dynamic enumerator, number

*** Required with conditions ***********************************************

entity_type (string)
  - if 'is_hierarchical' is set to False
  - type of entity
  - possibilities: task, show, assetversion, user, list, asset

config (dictionary)
   - for each entity type different requirements and possibilities:
       - enumerator:    multiSelect = True/False(default: False)
                        data = {key_1:value_1,key_2:value_2,..,key_n:value_n}
                        - 'data' is Required value with enumerator
                        - 'key' must contain only chars [a-z0-9_]

       - number:        isdecimal = True/False(default: False)

       - text:          markdown = True/False(default: False)

object_type (string)
  - IF ENTITY_TYPE is set to 'task'
  - default possibilities: Folder, Shot, Sequence, Task, Library,
                           Milestone, Episode, Asset Build,...

*** Optional ***************************************************************

write_security_roles/read_security_roles (array of strings)
  - default: ["ALL"]
  - strings should be role names (e.g.: ["API", "Administrator"])
  - if set to ["ALL"] - all roles will be availabled
  - if first is 'except' - roles will be set to all except roles in array
       - Warning: Be carefull with except - roles can be different by company
       - example:
          write_security_roles = ["except", "User"]
          read_security_roles = ["ALL"]
              - User is unable to write but can read

group (string)
  - default: None
  - name of group

default
  - default: None
  - sets default value for custom attribute:
       - text -> string
       - number -> integer
       - enumerator -> array with string of key/s
       - boolean -> bool true/false
       - date -> string in format: 'YYYY.MM.DD' or 'YYYY.MM.DD HH:mm:ss'
             - example: "2018.12.24" / "2018.1.1 6:0:0"
       - dynamic enumerator -> DON'T HAVE DEFAULT VALUE!!!

is_hierarchical (bool)
  - default: False
  - will set hierachical attribute
  - False by default

EXAMPLE:
{
    "avalon_auto_sync": {
        "label": "Avalon auto-sync",
        "key": "avalon_auto_sync",
        "type": "boolean",
        "entity_type": "show",
        "group": "avalon",
        "default": false,
        "write_security_role": ["API","Administrator"],
        "read_security_role": ["API","Administrator"]
    }
}
"""


class CustAttrException(Exception):
    pass


class CustomAttributes(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'create.update.attributes'
    #: Action label.
    label = "Pype Admin"
    variant = '- Create/Update Avalon Attributes'
    #: Action description.
    description = 'Creates Avalon/Mongo ID for double check'
    #: roles that are allowed to register this action
    role_list = ['Pypeclub', 'Administrator']
    icon = '{}/ftrack/action_icons/PypeAdmin.svg'.format(
        os.environ.get('PYPE_STATICS_SERVER', '')
    )

    required_keys = ['key', 'label', 'type']
    type_posibilities = [
        'text', 'boolean', 'date', 'enumerator',
        'dynamic enumerator', 'number'
    ]

    def discover(self, session, entities, event):
        '''
        Validation
        - action is only for Administrators
        '''
        return True

    def launch(self, session, entities, event):
        self.types = {}
        self.object_type_ids = {}
        self.groups = {}
        self.security_roles = None

        # JOB SETTINGS
        userId = event['source']['user']['id']
        user = session.query('User where id is ' + userId).one()

        job = session.create('Job', {
            'user': user,
            'status': 'running',
            'data': json.dumps({
                'description': 'Custom Attribute creation.'
            })
        })
        session.commit()
        try:
            self.avalon_mongo_id_attributes(session)
            self.custom_attributes_from_file(session, event)

            job['status'] = 'done'
            session.commit()

        except Exception as exc:
            session.rollback()
            job['status'] = 'failed'
            session.commit()
            self.log.error(
                'Creating custom attributes failed ({})'.format(exc),
                exc_info=True
            )

        return True

    def avalon_mongo_id_attributes(self, session):
        # Attribute Name and Label
        cust_attr_label = 'Avalon/Mongo Id'

        # Types that don't need object_type_id
        base = {'show'}

        # Don't create custom attribute on these entity types:
        exceptions = ['task', 'milestone']
        exceptions.extend(base)

        # Get all possible object types
        all_obj_types = session.query('ObjectType').all()

        # Filter object types by exceptions
        filtered_types_id = set()

        for obj_type in all_obj_types:
            name = obj_type['name']
            if " " in name:
                name = name.replace(' ', '')

            if obj_type['name'] not in self.object_type_ids:
                self.object_type_ids[name] = obj_type['id']

            if name.lower() not in exceptions:
                filtered_types_id.add(obj_type['id'])

        # Set security roles for attribute
        role_list = ("API", "Administrator", "Pypeclub")
        roles = self.get_security_roles(role_list)
        # Set Text type of Attribute
        custom_attribute_type = self.get_type('text')
        # Set group to 'avalon'
        group = self.get_group('avalon')

        data = {}
        data['key'] = CustAttrIdKey
        data['label'] = cust_attr_label
        data['type'] = custom_attribute_type
        data['default'] = ''
        data['write_security_roles'] = roles
        data['read_security_roles'] = roles
        data['group'] = group
        data['config'] = json.dumps({'markdown': False})

        for entity_type in base:
            data['entity_type'] = entity_type
            self.process_attribute(data)

        data['entity_type'] = 'task'
        for object_type_id in filtered_types_id:
            data['object_type_id'] = str(object_type_id)
            self.process_attribute(data)

    def convert_mongo_id_to_hierarchical(
        self, hierarchical_attr, object_type_attrs, session, event
    ):
        user_msg = "Converting old custom attributes. This may take some time."
        self.show_message(event, user_msg, True)
        self.log.info(user_msg)

        object_types_per_id = {
            object_type["id"]: object_type
            for object_type in session.query("ObjectType").all()
        }

        cust_attr_query = (
            "select value, entity_id from ContextCustomAttributeValue "
            "where configuration_id is {}"
        )
        for attr_def in object_type_attrs:
            attr_ent_type = attr_def["entity_type"]
            if attr_ent_type == "show":
                entity_type_label = "Project"
            elif attr_ent_type == "task":
                entity_type_label = (
                    object_types_per_id[attr_def["object_type_id"]]
                )
            else:
                self.log.warning(
                    "Unsupported entity type: \"{}\". Skipping.".format(
                        attr_ent_type
                    )
                )
                continue

            self.log.debug((
                "Converting Avalon MongoID attr for Entity type \"{}\"."
            ).format(entity_type_label))

            call_expr = [{
                "action": "query",
                "expression": cust_attr_query.format(attr_def["id"])
            }]
            if hasattr(session, "call"):
                [values] = session.call(call_expr)
            else:
                [values] = session._call(call_expr)

            for value in values["data"]:
                table_values = collections.OrderedDict({
                    "configuration_id": hierarchical_attr["id"],
                    "entity_id": value["entity_id"]
                })

                session.recorded_operations.push(
                    ftrack_api.operation.UpdateEntityOperation(
                        "ContextCustomAttributeValue",
                        table_values,
                        "value",
                        ftrack_api.symbol.NOT_SET,
                        value["value"]
                    )
                )

            try:
                session.commit()

            except Exception:
                session.rollback()
                self.log.warning(
                    (
                        "Couldn't transfer Avalon Mongo ID"
                        " attribute for entity type \"{}\"."
                    ).format(entity_type_label),
                    exc_info=True
                )

            try:
                session.delete(attr_def)
                session.commit()

            except Exception:
                session.rollback()
                self.log.warning(
                    (
                        "Couldn't delete Avalon Mongo ID"
                        " attribute for entity type \"{}\"."
                    ).format(entity_type_label),
                    exc_info=True
                )

    def custom_attributes_from_file(self, session, event):
        presets = config.get_presets()['ftrack']['ftrack_custom_attributes']

        for cust_attr_data in presets:
            cust_attr_name = cust_attr_data.get(
                'label',
                cust_attr_data.get('key')
            )
            try:
                data = {}
                # Get key, label, type
                data.update(self.get_required(cust_attr_data))
                # Get hierachical/ entity_type/ object_id
                data.update(self.get_entity_type(cust_attr_data))
                # Get group, default, security roles
                data.update(self.get_optional(cust_attr_data))
                # Process data
                self.process_attribute(data)

            except CustAttrException as cae:
                if cust_attr_name:
                    msg = 'Custom attribute error "{}" - {}'.format(
                        cust_attr_name, str(cae)
                    )
                else:
                    msg = 'Custom attribute error - {}'.format(str(cae))
                self.log.warning(msg, exc_info=True)
                self.show_message(event, msg)

        return True

    def process_attribute(self, data):
        existing_atr = self.session.query('CustomAttributeConfiguration').all()
        matching = []
        for attr in existing_atr:
            if (
                attr['key'] != data['key'] or
                attr['type']['name'] != data['type']['name']
            ):
                continue

            if data.get('is_hierarchical', False) is True:
                if attr['is_hierarchical'] is True:
                    matching.append(attr)
            elif 'object_type_id' in data:
                if (
                    attr['entity_type'] == data['entity_type'] and
                    attr['object_type_id'] == data['object_type_id']
                ):
                    matching.append(attr)
            else:
                if attr['entity_type'] == data['entity_type']:
                    matching.append(attr)

        if len(matching) == 0:
            self.session.create('CustomAttributeConfiguration', data)
            self.session.commit()
            self.log.debug(
                '{}: "{}" created'.format(self.label, data['label'])
            )

        elif len(matching) == 1:
            attr_update = matching[0]
            for key in data:
                if (
                    key not in [
                        'is_hierarchical', 'entity_type', 'object_type_id'
                    ]
                ):
                    attr_update[key] = data[key]

            self.log.debug(
                '{}: "{}" updated'.format(self.label, data['label'])
            )
            self.session.commit()

        else:
            raise CustAttrException('Is duplicated')

    def get_required(self, attr):
        output = {}
        for key in self.required_keys:
            if key not in attr:
                raise CustAttrException(
                    'Key {} is required - please set'.format(key)
                )

        if attr['type'].lower() not in self.type_posibilities:
            raise CustAttrException(
                'Type {} is not valid'.format(attr['type'])
            )

        type_name = attr['type'].lower()

        output['key'] = attr['key']
        output['label'] = attr['label']
        output['type'] = self.get_type(type_name)

        config = None
        if type_name == 'number':
            config = self.get_number_config(attr)
        elif type_name == 'text':
            config = self.get_text_config(attr)
        elif type_name == 'enumerator':
            config = self.get_enumerator_config(attr)

        if config is not None:
            output['config'] = config

        return output

    def get_number_config(self, attr):
        if 'config' in attr and 'isdecimal' in attr['config']:
            isdecimal = attr['config']['isdecimal']
        else:
            isdecimal = False

        config = json.dumps({'isdecimal': isdecimal})

        return config

    def get_text_config(self, attr):
        if 'config' in attr and 'markdown' in attr['config']:
            markdown = attr['config']['markdown']
        else:
            markdown = False
        config = json.dumps({'markdown': markdown})

        return config

    def get_enumerator_config(self, attr):
        if 'config' not in attr:
            raise CustAttrException('Missing config with data')
        if 'data' not in attr['config']:
            raise CustAttrException('Missing data in config')

        data = []
        for item in attr['config']['data']:
            item_data = {}
            for key in item:
                # TODO key check by regex
                item_data['menu'] = item[key]
                item_data['value'] = key
                data.append(item_data)

        multiSelect = False
        for k in attr['config']:
            if k.lower() == 'multiselect':
                if isinstance(attr['config'][k], bool):
                    multiSelect = attr['config'][k]
                else:
                    raise CustAttrException('Multiselect must be boolean')
                break

        config = json.dumps({
            'multiSelect': multiSelect,
            'data': json.dumps(data)
        })

        return config

    def get_group(self, attr):
        if isinstance(attr, dict):
            group_name = attr['group'].lower()
        else:
            group_name = attr
        if group_name in self.groups:
            return self.groups[group_name]

        query = 'CustomAttributeGroup where name is "{}"'.format(group_name)
        groups = self.session.query(query).all()

        if len(groups) == 1:
            group = groups[0]
            self.groups[group_name] = group

            return group

        elif len(groups) < 1:
            group = self.session.create('CustomAttributeGroup', {
                'name': group_name,
            })
            self.session.commit()

            return group

        else:
            raise CustAttrException(
                'Found more than one group "{}"'.format(group_name)
            )

    def query_roles(self):
        if self.security_roles is None:
            self.security_roles = {}
            for role in self.session.query("SecurityRole").all():
                key = role["name"].lower()
                self.security_roles[key] = role
        return self.security_roles

    def get_security_roles(self, security_roles):
        security_roles = self.query_roles()

        security_roles_lowered = tuple(name.lower() for name in security_roles)
        if (
            len(security_roles_lowered) == 0
            or "all" in security_roles_lowered
        ):
            return tuple(security_roles.values())

        output = []
        if security_roles_lowered[0] == "except":
            excepts = security_roles_lowered[1:]
            for role_name, role in security_roles.items():
                if role_name not in excepts:
                    output.append(role)

        else:
            for role_name in security_roles_lowered:
                if role_name in security_roles:
                    output.append(security_roles[role_name])
                else:
                    raise CustAttrException((
                        "Securit role \"{}\" was not found in Ftrack."
                    ).format(role_name))
        return output

    def get_default(self, attr):
        type = attr['type']
        default = attr['default']
        if default is None:
            return default
        err_msg = 'Default value is not'
        if type == 'number':
            if not isinstance(default, (float, int)):
                raise CustAttrException('{} integer'.format(err_msg))
        elif type == 'text':
            if not isinstance(default, str):
                raise CustAttrException('{} string'.format(err_msg))
        elif type == 'boolean':
            if not isinstance(default, bool):
                raise CustAttrException('{} boolean'.format(err_msg))
        elif type == 'enumerator':
            if not isinstance(default, list):
                raise CustAttrException(
                    '{} array with strings'.format(err_msg)
                )
            # TODO check if multiSelect is available
            # and if default is one of data menu
            if not isinstance(default[0], str):
                raise CustAttrException('{} array of strings'.format(err_msg))
        elif type == 'date':
            date_items = default.split(' ')
            try:
                if len(date_items) == 1:
                    default = arrow.get(default, 'YY.M.D')
                elif len(date_items) == 2:
                    default = arrow.get(default, 'YY.M.D H:m:s')
                else:
                    raise Exception
            except Exception:
                raise CustAttrException('Date is not in proper format')
        elif type == 'dynamic enumerator':
            raise CustAttrException('Dynamic enumerator can\'t have default')

        return default

    def get_optional(self, attr):
        output = {}
        if 'group' in attr:
            output['group'] = self.get_group(attr)
        if 'default' in attr:
            output['default'] = self.get_default(attr)

        roles_read = []
        roles_write = []
        if 'read_security_roles' in output:
            roles_read = attr['read_security_roles']
        if 'read_security_roles' in output:
            roles_write = attr['write_security_roles']
        output['read_security_roles'] = self.get_security_roles(roles_read)
        output['write_security_roles'] = self.get_security_roles(roles_write)

        return output

    def get_type(self, type_name):
        if type_name in self.types:
            return self.types[type_name]

        query = 'CustomAttributeType where name is "{}"'.format(type_name)
        type = self.session.query(query).one()
        self.types[type_name] = type

        return type

    def get_entity_type(self, attr):
        if 'is_hierarchical' in attr:
            if attr['is_hierarchical'] is True:
                type = 'show'
                if 'entity_type' in attr:
                    type = attr['entity_type']

                return {
                    'is_hierarchical': True,
                    'entity_type': type
                }

        if 'entity_type' not in attr:
            raise CustAttrException('Missing entity_type')

        if attr['entity_type'].lower() != 'task':
            return {'entity_type': attr['entity_type']}

        if 'object_type' not in attr:
            raise CustAttrException('Missing object_type')

        object_type_name = attr['object_type']
        if object_type_name not in self.object_type_ids:
            try:
                query = 'ObjectType where name is "{}"'.format(
                    object_type_name
                )
                object_type_id = self.session.query(query).one()['id']
            except Exception:
                raise CustAttrException((
                    'Object type with name "{}" don\'t exist'
                ).format(object_type_name))
            self.object_type_ids[object_type_name] = object_type_id
        else:
            object_type_id = self.object_type_ids[object_type_name]

        return {
            'entity_type': attr['entity_type'],
            'object_type_id': object_type_id
        }


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    CustomAttributes(session, plugins_presets).register()
