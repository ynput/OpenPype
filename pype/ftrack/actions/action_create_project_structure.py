import os
import sys
import re
import argparse
import logging

import ftrack_api
from pype.ftrack import BaseAction
from pypeapp import config


class CreateProjectFolders(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'create.project.structure'
    #: Action label.
    label = 'Create Project Structure'
    #: Action description.
    description = 'Creates folder structure'
    #: roles that are allowed to register this action
    role_list = ['Pypeclub', 'Administrator', 'Project Manager']
    icon = '{}/ftrack/action_icons/CreateProjectFolders.svg'.format(
        os.environ.get('PYPE_STATICS_SERVER', '')
    )

    pattern_array = re.compile('\[.*\]')
    pattern_ftrack = '.*\[[.]*ftrack[.]*'
    pattern_ent_ftrack = 'ftrack\.[^.,\],\s,]*'
    project_root_key = '__project_root__'

    def discover(self, session, entities, event):
        ''' Validation '''
        if len(entities) != 1:
            return False

        if entities[0].entity_type.lower() != "project":
            return False

        return True

    def launch(self, session, entities, event):
        entity = entities[0]
        if entity.entity_type.lower() == 'project':
            project = entity
        else:
            project = entity['project']

        presets = config.get_presets()['tools']['project_folder_structure']
        try:
            # Get paths based on presets
            basic_paths = self.get_path_items(presets)
            self.create_folders(basic_paths, entity)
            self.create_ftrack_entities(basic_paths, project)
        except Exception as e:
            session.rollback()
            return {
                'success': False,
                'message': str(e)
            }

        return True

    def get_ftrack_paths(self, paths_items):
        all_ftrack_paths = []
        for path_items in paths_items:
            ftrack_path_items = []
            is_ftrack = False
            for item in reversed(path_items):
                if item == self.project_root_key:
                    continue
                if is_ftrack:
                    ftrack_path_items.append(item)
                elif re.match(self.pattern_ftrack, item):
                    ftrack_path_items.append(item)
                    is_ftrack = True
            ftrack_path_items = list(reversed(ftrack_path_items))
            if ftrack_path_items:
                all_ftrack_paths.append(ftrack_path_items)
        return all_ftrack_paths

    def compute_ftrack_items(self, in_list, keys):
        if len(keys) == 0:
            return in_list
        key = keys[0]
        exist = None
        for index, subdict in enumerate(in_list):
            if key in subdict:
                exist = index
                break
        if exist is not None:
            in_list[exist][key] = self.compute_ftrack_items(
                in_list[exist][key], keys[1:]
            )
        else:
            in_list.append({key: self.compute_ftrack_items([], keys[1:])})
        return in_list

    def translate_ftrack_items(self, paths_items):
        main = []
        for path_items in paths_items:
            main = self.compute_ftrack_items(main, path_items)
        return main

    def create_ftrack_entities(self, basic_paths, project_ent):
        only_ftrack_items = self.get_ftrack_paths(basic_paths)
        ftrack_paths = self.translate_ftrack_items(only_ftrack_items)

        for separation in ftrack_paths:
            parent = project_ent
            self.trigger_creation(separation, parent)

    def trigger_creation(self, separation, parent):
        for item, subvalues in separation.items():
            matches = re.findall(self.pattern_array, item)
            ent_type = 'Folder'
            if len(matches) == 0:
                name = item
            else:
                match = matches[0]
                name = item.replace(match, '')
                ent_type_match = re.findall(self.pattern_ent_ftrack, match)
                if len(ent_type_match) > 0:
                    ent_type_split = ent_type_match[0].split('.')
                    if len(ent_type_split) == 2:
                        ent_type = ent_type_split[1]
            new_parent = self.create_ftrack_entity(name, ent_type, parent)
            if subvalues:
                for subvalue in subvalues:
                    self.trigger_creation(subvalue, new_parent)

    def create_ftrack_entity(self, name, ent_type, parent):
        for children in parent['children']:
            if children['name'] == name:
                return children
        data = {
            'name': name,
            'parent_id': parent['id']
        }
        if parent.entity_type.lower() == 'project':
            data['project_id'] = parent['id']
        else:
            data['project_id'] = parent['project']['id']

        existing_entity = self.session.query((
            "TypedContext where name is \"{}\" and "
            "parent_id is \"{}\" and project_id is \"{}\""
        ).format(name, data['parent_id'], data['project_id'])).first()
        if existing_entity:
            return existing_entity

        new_ent = self.session.create(ent_type, data)
        self.session.commit()
        return new_ent

    def get_path_items(self, in_dict):
        output = []
        for key, value in in_dict.items():
            if not value:
                output.append(key)
            else:
                paths = self.get_path_items(value)
                for path in paths:
                    if isinstance(path, str):
                        output.append([key, path])
                    else:
                        p = [key]
                        p.extend(path)
                        output.append(p)
        return output

    def compute_paths(self, basic_paths_items, project_root):
        output = []
        for path_items in basic_paths_items:
            clean_items = []
            for path_item in path_items:
                matches = re.findall(self.pattern_array, path_item)
                if len(matches) > 0:
                    path_item = path_item.replace(matches[0], '')
                if path_item == self.project_root_key:
                    path_item = project_root
                clean_items.append(path_item)
            output.append(os.path.normpath(os.path.sep.join(clean_items)))
        return output

    def create_folders(self, basic_paths, entity):
        # Set project root folder
        if entity.entity_type.lower() == 'project':
            project_name = entity['full_name']
        else:
            project_name = entity['project']['full_name']
        project_root_items = [os.environ['AVALON_PROJECTS'], project_name]
        project_root = os.path.sep.join(project_root_items)

        full_paths = self.compute_paths(basic_paths, project_root)
        #Create folders
        for path in full_paths:
            if os.path.exists(path):
                continue
            os.makedirs(path.format(project_root=project_root))




def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    CreateProjectFolders(session, plugins_presets).register()


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
