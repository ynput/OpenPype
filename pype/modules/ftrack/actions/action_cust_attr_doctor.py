import os
import sys
import json
import argparse
import logging

import ftrack_api
from pype.modules.ftrack import BaseAction


class CustomAttributeDoctor(BaseAction):

    ignore_me = True
    #: Action identifier.
    identifier = 'custom.attributes.doctor'
    #: Action label.
    label = "Pype Doctor"
    variant = '- Custom Attributes Doctor'
    #: Action description.
    description = (
        'Fix hierarchical custom attributes mainly handles, fstart'
        ' and fend'
    )

    icon = '{}/ftrack/action_icons/PypeDoctor.svg'.format(
        os.environ.get('PYPE_STATICS_SERVER', '')
    )
    hierarchical_ca = ['handleStart', 'handleEnd', 'frameStart', 'frameEnd']
    hierarchical_alternatives = {
        'handleStart': 'handles',
        'handleEnd': 'handles',
        "frameStart": "fstart",
        "frameEnd": "fend"
    }

    # Roles for new custom attributes
    read_roles = ['ALL',]
    write_roles = ['ALL',]

    data_ca = {
        'handleStart': {
            'label': 'Frame handles start',
            'type': 'number',
            'config': json.dumps({'isdecimal': False})
        },
        'handleEnd': {
            'label': 'Frame handles end',
            'type': 'number',
            'config': json.dumps({'isdecimal': False})
        },
        'frameStart': {
            'label': 'Frame start',
            'type': 'number',
            'config': json.dumps({'isdecimal': False})
        },
        'frameEnd': {
            'label': 'Frame end',
            'type': 'number',
            'config': json.dumps({'isdecimal': False})
        }
    }

    def discover(self, session, entities, event):
        ''' Validation '''

        return True

    def interface(self, session, entities, event):
        if event['data'].get('values', {}):
            return

        title = 'Select Project to fix Custom attributes'

        items = []
        item_splitter = {'type': 'label', 'value': '---'}

        all_projects = session.query('Project').all()
        for project in all_projects:
            item_label = {
                'type': 'label',
                'value': '{} (<i>{}</i>)'.format(
                    project['full_name'], project['name']
                )
            }
            item = {
                'name': project['id'],
                'type': 'boolean',
                'value': False
            }
            if len(items) > 0:
                items.append(item_splitter)
            items.append(item_label)
            items.append(item)

        if len(items) == 0:
            return {
                'success': False,
                'message': 'Didn\'t found any projects'
            }
        else:
            return {
                'items': items,
                'title': title
            }

    def launch(self, session, entities, event):
        if 'values' not in event['data']:
            return

        values = event['data']['values']
        projects_to_update = []
        for project_id, update_bool in values.items():
            if not update_bool:
                continue

            project = session.query(
                'Project where id is "{}"'.format(project_id)
            ).one()
            projects_to_update.append(project)

        if not projects_to_update:
            self.log.debug('Nothing to update')
            return {
                'success': True,
                'message': 'Nothing to update'
            }

        self.security_roles = {}
        self.to_process = {}
        # self.curent_default_values = {}
        existing_attrs = session.query('CustomAttributeConfiguration').all()
        self.prepare_custom_attributes(existing_attrs)

        self.projects_data = {}
        for project in projects_to_update:
            self.process_data(project)

        return True

    def process_data(self, entity):
        cust_attrs = entity.get('custom_attributes')
        if not cust_attrs:
            return
        for dst_key, src_key in self.to_process.items():
            if src_key in cust_attrs:
                value = cust_attrs[src_key]
                entity['custom_attributes'][dst_key] = value
                self.session.commit()

        for child in entity.get('children', []):
            self.process_data(child)

    def prepare_custom_attributes(self, existing_attrs):
        to_process = {}
        to_create = []
        all_keys = {attr['key']: attr for attr in existing_attrs}
        for key in self.hierarchical_ca:
            if key not in all_keys:
                self.log.debug(
                    'Custom attribute "{}" does not exist at all'.format(key)
                )
                to_create.append(key)
                if key in self.hierarchical_alternatives:
                    alt_key = self.hierarchical_alternatives[key]
                    if alt_key in all_keys:
                        self.log.debug((
                            'Custom attribute "{}" will use values from "{}"'
                        ).format(key, alt_key))

                        to_process[key] = alt_key

                        obj = all_keys[alt_key]
                        # if alt_key not in self.curent_default_values:
                        #     self.curent_default_values[alt_key] = obj['default']
                        obj['default'] = None
                        self.session.commit()

            else:
                obj = all_keys[key]
                new_key = key + '_old'

                if obj['is_hierarchical']:
                    if new_key not in all_keys:
                        self.log.info((
                            'Custom attribute "{}" is already hierarchical'
                            ' and can\'t find old one'
                            ).format(key)
                        )
                        continue

                    to_process[key] = new_key
                    continue

                # default_value = obj['default']
                # if new_key not in self.curent_default_values:
                #     self.curent_default_values[new_key] = default_value

                obj['key'] = new_key
                obj['label'] = obj['label'] + '(old)'
                obj['default'] = None

                self.session.commit()

                to_create.append(key)
                to_process[key] = new_key

        self.to_process = to_process
        for key in to_create:
            data = {
                'key': key,
                'entity_type': 'show',
                'is_hierarchical': True,
                'default': None
            }
            for _key, _value in self.data_ca.get(key, {}).items():
                if _key == 'type':
                    _value = self.session.query((
                        'CustomAttributeType where name is "{}"'
                    ).format(_value)).first()

                data[_key] = _value

            avalon_group = self.session.query(
                'CustomAttributeGroup where name is "avalon"'
            ).first()
            if avalon_group:
                data['group'] = avalon_group

            read_roles = self.get_security_role(self.read_roles)
            write_roles = self.get_security_role(self.write_roles)
            data['read_security_roles'] = read_roles
            data['write_security_roles'] = write_roles

            self.session.create('CustomAttributeConfiguration', data)
            self.session.commit()

    # def return_back_defaults(self):
    #     existing_attrs = self.session.query(
    #         'CustomAttributeConfiguration'
    #     ).all()
    #
    #     for attr_key, default in self.curent_default_values.items():
    #         for attr in existing_attrs:
    #             if attr['key'] != attr_key:
    #                 continue
    #             attr['default'] = default
    #             self.session.commit()
    #             break

    def get_security_role(self, security_roles):
        roles = []
        if len(security_roles) == 0 or security_roles[0] == 'ALL':
            roles = self.get_role_ALL()
        elif security_roles[0] == 'except':
            excepts = security_roles[1:]
            all = self.get_role_ALL()
            for role in all:
                if role['name'] not in excepts:
                    roles.append(role)
                if role['name'] not in self.security_roles:
                    self.security_roles[role['name']] = role
        else:
            for role_name in security_roles:
                if role_name in self.security_roles:
                    roles.append(self.security_roles[role_name])
                    continue

                try:
                    query = 'SecurityRole where name is "{}"'.format(role_name)
                    role = self.session.query(query).one()
                    self.security_roles[role_name] = role
                    roles.append(role)
                except Exception:
                    self.log.warning(
                        'Securit role "{}" does not exist'.format(role_name)
                    )
                    continue

        return roles

    def get_role_ALL(self):
        role_name = 'ALL'
        if role_name in self.security_roles:
            all_roles = self.security_roles[role_name]
        else:
            all_roles = self.session.query('SecurityRole').all()
            self.security_roles[role_name] = all_roles
            for role in all_roles:
                if role['name'] not in self.security_roles:
                    self.security_roles[role['name']] = role
        return all_roles


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    CustomAttributeDoctor(session, plugins_presets).register()


def main(arguments=None):
    '''Set up logging and register action.'''
    if arguments is None:
        arguments = []

    parser = argparse.ArgumentParser()
    # Allow setting of logging level from arguments.
    loggingLevels = {}
    for level in (
        logging.NOTSET, logging.DEBUG, logging.INFO, logging.WARNING,
        logging.ERROR, logging.CRITICAL
    ):
        loggingLevels[logging.getLevelName(level).lower()] = level

    parser.add_argument(
        '-v', '--verbosity',
        help='Set the logging output verbosity.',
        choices=loggingLevels.keys(),
        default='info'
    )
    namespace = parser.parse_args(arguments)

    # Set up basic logging
    logging.basicConfig(level=loggingLevels[namespace.verbosity])

    session = ftrack_api.Session()
    register(session)

    # Wait for events
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
