import logging
import os
import argparse
import sys
import errno

import ftrack_api
from pype.ftrack import BaseAction
import json
from pype import api as pype


class CreateFolders(BaseAction):

    '''Custom action.'''

    #: Action identifier.
    identifier = 'create.folders'

    #: Action label.
    label = 'Create Folders'

    #: Action Icon.
    icon = (
        'https://cdn1.iconfinder.com/data/icons/hawcons/32/'
        '698620-icon-105-folder-add-512.png'
    )

    def discover(self, session, entities, event):
        ''' Validation '''
        not_allowed = ['assetversion']
        if len(entities) != 1:
            return False
        if entities[0].entity_type.lower() in not_allowed:
            return False
        return True


    def launch(self, session, entities, event):
        '''Callback method for custom action.'''

        #######################################################################

        # JOB SETTINGS
        userId = event['source']['user']['id']
        user = session.query('User where id is ' + userId).one()

        job = session.create('Job', {
            'user': user,
            'status': 'running',
            'data': json.dumps({
                'description': 'Creating Folders.'
            })
        })

        try:
            self.importable = set([])
            # self.importable = []

            self.Anatomy = pype.Anatomy

            project = entities[0]['project']

            paths_collected = set([])

            # get all child entities separately/unique
            for entity in entities:
                self.getShotAsset(entity)

            for ent in self.importable:
                self.log.info("{}".format(ent['name']))

            for entity in self.importable:
                print(entity['name'])

                anatomy = pype.Anatomy
                parents = entity['link']

                hierarchy_names = []
                for p in parents[1:-1]:
                    hierarchy_names.append(p['name'])

                if hierarchy_names:
                    # hierarchy = os.path.sep.join(hierarchy)
                    hierarchy = os.path.join(*hierarchy_names)

                template_data = {"project": {"name": project['full_name'],
                                             "code": project['name']},
                                 "asset": entity['name'],
                                 "hierarchy": hierarchy}

                for task in entity['children']:
                    if task['object_type']['name'] == 'Task':
                        self.log.info('child: {}'.format(task['name']))
                        template_data['task'] = task['name']
                        anatomy_filled = anatomy.format(template_data)
                        paths_collected.add(anatomy_filled.work.folder)
                        paths_collected.add(anatomy_filled.publish.folder)

            for path in paths_collected:
                self.log.info(path)
                try:
                    os.makedirs(path)
                except OSError as error:
                    if error.errno != errno.EEXIST:
                        raise

            job['status'] = 'done'
            session.commit()

        except ValueError as ve:
            job['status'] = 'failed'
            session.commit()
            message = str(ve)
            self.log.error('Error during syncToAvalon: {}'.format(message))

        except Exception:
            job['status'] = 'failed'
            session.commit()

        #######################################################################

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

    def get_presets(self):
        fpath_items = [pypelib.get_presets_path(), 'tools', 'sw_folders.json']
        filepath = os.path.normpath(os.path.sep.join(fpath_items))
        presets = dict()
        try:
            with open(filepath) as data_file:
                presets = json.load(data_file)
        except Exception as e:
            self.log.warning('Wasn\'t able to load presets')
        return dict(presets)

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

    def compute_template(self, str, data):
        first_result = self.template_format(str, data)
        if first_result == first_result.split('{')[0]:
            return os.path.normpath(first_result)

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


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    CreateFolders(session).register()


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
