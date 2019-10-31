import os
import sys
import logging
import argparse
import re

from pype.vendor import ftrack_api
from pype.ftrack import BaseAction
from avalon import lib as avalonlib
from pype.ftrack.lib.io_nonsingleton import DbConnector
from pypeapp import config, Anatomy


class CreateFolders(BaseAction):

    '''Custom action.'''

    #: Action identifier.
    identifier = 'create.folders'

    #: Action label.
    label = 'Create Folders'

    #: Action Icon.
    icon = '{}/ftrack/action_icons/CreateFolders.svg'.format(
        os.environ.get('PYPE_STATICS_SERVER', '')
    )

    db = DbConnector()

    def discover(self, session, entities, event):
        ''' Validation '''
        if len(entities) != 1:
            return False

        not_allowed = ['assetversion', 'project']
        if entities[0].entity_type.lower() in not_allowed:
            return False

        return True

    def interface(self, session, entities, event):
        if event['data'].get('values', {}):
            return
        entity = entities[0]
        without_interface = True
        for child in entity['children']:
            if child['object_type']['name'].lower() != 'task':
                without_interface = False
                break
        self.without_interface = without_interface
        if without_interface:
            return
        title = 'Create folders'

        entity_name = entity['name']
        msg = (
            '<h2>Do you want create folders also'
            ' for all children of "{}"?</h2>'
        )
        if entity.entity_type.lower() == 'project':
            entity_name = entity['full_name']
            msg = msg.replace(' also', '')
            msg += '<h3>(Project root won\'t be created if not checked)</h3>'
        items = []
        item_msg = {
            'type': 'label',
            'value': msg.format(entity_name)
        }
        item_label = {
            'type': 'label',
            'value': 'With all chilren entities'
        }
        item = {
            'name': 'children_included',
            'type': 'boolean',
            'value': False
        }
        items.append(item_msg)
        items.append(item_label)
        items.append(item)

        if len(items) == 0:
            return {
                'success': False,
                'message': 'Didn\'t found any running jobs'
            }
        else:
            return {
                'items': items,
                'title': title
            }

    def launch(self, session, entities, event):
        '''Callback method for custom action.'''
        with_childrens = True
        if self.without_interface is False:
            if 'values' not in event['data']:
                return
            with_childrens = event['data']['values']['children_included']
        entity = entities[0]
        if entity.entity_type.lower() == 'project':
            proj = entity
        else:
            proj = entity['project']
        project_name = proj['full_name']
        project_code = proj['name']
        if entity.entity_type.lower() == 'project' and with_childrens == False:
            return {
                'success': True,
                'message': 'Nothing was created'
            }
        data = {
            "root": os.environ["AVALON_PROJECTS"],
            "project": {
                "name": project_name,
                "code": project_code
            }
        }
        all_entities = []
        all_entities.append(entity)
        if with_childrens:
            all_entities = self.get_notask_children(entity)

        av_project = None
        try:
            self.db.install()
            self.db.Session['AVALON_PROJECT'] = project_name
            av_project = self.db.find_one({'type': 'project'})
            template_work = av_project['config']['template']['work']
            template_publish = av_project['config']['template']['publish']
            self.db.uninstall()
        except Exception:
            templates = Anatomy().templates
            template_work = templates["avalon"]["work"]
            template_publish = templates["avalon"]["publish"]

        collected_paths = []
        presets = config.get_presets()['tools']['sw_folders']
        for entity in all_entities:
            if entity.entity_type.lower() == 'project':
                continue
            ent_data = data.copy()

            asset_name = entity['name']
            ent_data['asset'] = asset_name

            parents = entity['link']
            hierarchy_names = [p['name'] for p in parents[1:-1]]
            hierarchy = ''
            if hierarchy_names:
                hierarchy = os.path.sep.join(hierarchy_names)
            ent_data['hierarchy'] = hierarchy

            tasks_created = False
            if entity['children']:
                for child in entity['children']:
                    if child['object_type']['name'].lower() != 'task':
                        continue
                    tasks_created = True
                    task_type_name = child['type']['name'].lower()
                    task_data = ent_data.copy()
                    task_data['task'] = child['name']
                    possible_apps = presets.get(task_type_name, [])
                    template_work_created = False
                    template_publish_created = False
                    apps = []
                    for app in possible_apps:
                        try:
                            app_data = avalonlib.get_application(app)
                            app_dir = app_data['application_dir']
                        except ValueError:
                            app_dir = app
                        apps.append(app_dir)

                    # Template wok
                    if '{app}' in template_work:
                        for app in apps:
                            template_work_created = True
                            app_data = task_data.copy()
                            app_data['app'] = app
                            collected_paths.append(
                                self.compute_template(
                                    template_work, app_data
                                )
                            )
                    if template_work_created is False:
                        collected_paths.append(
                            self.compute_template(template_work, task_data)
                        )
                    # Template publish
                    if '{app}' in template_publish:
                        for app in apps:
                            template_publish_created = True
                            app_data = task_data.copy()
                            app_data['app'] = app
                            collected_paths.append(
                                self.compute_template(
                                    template_publish, app_data, True
                                )
                            )
                    if template_publish_created is False:
                        collected_paths.append(
                            self.compute_template(
                                template_publish, task_data, True
                            )
                        )

            if not tasks_created:
                # create path for entity
                collected_paths.append(
                    self.compute_template(template_work, ent_data)
                )
                collected_paths.append(
                    self.compute_template(template_publish, ent_data)
                )
        if len(collected_paths) > 0:
            self.log.info('Creating folders:')
        for path in set(collected_paths):
            self.log.info(path)
            if not os.path.exists(path):
                os.makedirs(path)

        return {
            'success': True,
            'message': 'Created Folders Successfully!'
        }

    def get_notask_children(self, entity):
        output = []
        if entity.get('object_type', {}).get(
            'name', entity.entity_type
        ).lower() == 'task':
            return output
        else:
            output.append(entity)
        if entity['children']:
            for child in entity['children']:
                output.extend(self.get_notask_children(child))
        return output

    def template_format(self, template, data):

        partial_data = PartialDict(data)

        # remove subdict items from string (like 'project[name]')
        subdict = PartialDict()
        count = 1
        store_pattern = 5*'_'+'{:0>3}'
        regex_patern = "\{\w*\[[^\}]*\]\}"
        matches = re.findall(regex_patern, template)

        for match in matches:
            key = store_pattern.format(count)
            subdict[key] = match
            template = template.replace(match, '{'+key+'}')
            count += 1
        # solve fillind keys with optional keys
        solved = self._solve_with_optional(template, partial_data)
        # try to solve subdict and replace them back to string
        for k, v in subdict.items():
            try:
                v = v.format_map(data)
            except (KeyError, TypeError):
                pass
            subdict[k] = v

        return solved.format_map(subdict)

    def _solve_with_optional(self, template, data):
            # Remove optional missing keys
            pattern = re.compile(r"(<.*?[^{0]*>)[^0-9]*?")
            invalid_optionals = []
            for group in pattern.findall(template):
                try:
                    group.format(**data)
                except KeyError:
                    invalid_optionals.append(group)
            for group in invalid_optionals:
                template = template.replace(group, "")

            solved = template.format_map(data)

            # solving after format optional in second round
            for catch in re.compile(r"(<.*?[^{0]*>)[^0-9]*?").findall(solved):
                if "{" in catch:
                    # remove all optional
                    solved = solved.replace(catch, "")
                else:
                    # Remove optional symbols
                    solved = solved.replace(catch, catch[1:-1])

            return solved

    def compute_template(self, str, data, task=False):
        first_result = self.template_format(str, data)
        if first_result == first_result.split('{')[0]:
            return os.path.normpath(first_result)
        if task:
            return os.path.normpath(first_result.split('{')[0])

        index = first_result.index('{')

        regex = '\{\w*[^\}]*\}'
        match = re.findall(regex, first_result[index:])[0]
        without_missing = str.split(match)[0].split('}')
        output_items = []
        for part in without_missing:
            if '{' in part:
                output_items.append(part + '}')
        return os.path.normpath(
            self.template_format(''.join(output_items), data)
        )


class PartialDict(dict):
    def __getitem__(self, item):
        out = super().__getitem__(item)
        if isinstance(out, dict):
            return '{'+item+'}'
        return out

    def __missing__(self, key):
        return '{'+key+'}'


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    CreateFolders(session, plugins_presets).register()


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
