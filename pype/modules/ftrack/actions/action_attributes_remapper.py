import os

import ftrack_api
from pype.modules.ftrack import BaseAction
from pype.modules.ftrack.lib.io_nonsingleton import DbConnector


class AttributesRemapper(BaseAction):
    '''Edit meta data action.'''

    ignore_me = True
    #: Action identifier.
    identifier = 'attributes.remapper'
    #: Action label.
    label = "Pype Doctor"
    variant = '- Attributes Remapper'
    #: Action description.
    description = 'Remaps attributes in avalon DB'

    #: roles that are allowed to register this action
    role_list = ["Pypeclub", "Administrator"]
    icon = '{}/ftrack/action_icons/PypeDoctor.svg'.format(
        os.environ.get('PYPE_STATICS_SERVER', '')
    )

    db_con = DbConnector()
    keys_to_change = {
        "fstart": "frameStart",
        "startFrame": "frameStart",
        "edit_in": "frameStart",

        "fend": "frameEnd",
        "endFrame": "frameEnd",
        "edit_out": "frameEnd",

        "handle_start": "handleStart",
        "handle_end": "handleEnd",
        "handles": ["handleEnd", "handleStart"],

        "frameRate": "fps",
        "framerate": "fps",
        "resolution_width": "resolutionWidth",
        "resolution_height": "resolutionHeight",
        "pixel_aspect": "pixelAspect"
    }

    def discover(self, session, entities, event):
        ''' Validation '''

        return True

    def interface(self, session, entities, event):
        if event['data'].get('values', {}):
            return

        title = 'Select Projects where attributes should be remapped'

        items = []

        selection_enum = {
            'label': 'Process type',
            'type': 'enumerator',
            'name': 'process_type',
            'data': [
                {
                    'label': 'Selection',
                    'value': 'selection'
                }, {
                    'label': 'Inverted selection',
                    'value': 'except'
                }
            ],
            'value': 'selection'
        }
        selection_label = {
            'type': 'label',
            'value': (
                'Selection based variants:<br/>'
                '- `Selection` - '
                'NOTHING is processed when nothing is selected<br/>'
                '- `Inverted selection` - '
                'ALL Projects are processed when nothing is selected'
            )
        }

        items.append(selection_enum)
        items.append(selection_label)

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
        process_type = values.pop('process_type')

        selection = True
        if process_type == 'except':
            selection = False

        interface_messages = {}

        projects_to_update = []
        for project_id, update_bool in values.items():
            if not update_bool and selection:
                continue

            if update_bool and not selection:
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


        self.db_con.install()

        relevant_types = ["project", "asset", "version"]

        for ft_project in projects_to_update:
            self.log.debug(
                "Processing project \"{}\"".format(ft_project["full_name"])
            )

            self.db_con.Session["AVALON_PROJECT"] = ft_project["full_name"]
            project = self.db_con.find_one({'type': 'project'})
            if not project:
                key = "Projects not synchronized to db"
                if key not in interface_messages:
                    interface_messages[key] = []
                interface_messages[key].append(ft_project["full_name"])
                continue

            # Get all entities in project collection from MongoDB
            _entities = self.db_con.find({})
            for _entity in _entities:
                ent_t = _entity.get("type", "*unknown type")
                name = _entity.get("name", "*unknown name")

                self.log.debug(
                    "- {} ({})".format(name, ent_t)
                )

                # Skip types that do not store keys to change
                if ent_t.lower() not in relevant_types:
                    self.log.debug("-- skipping - type is not relevant")
                    continue

                # Get data which will change
                updating_data = {}
                source_data = _entity["data"]

                for key_from, key_to in self.keys_to_change.items():
                    # continue if final key already exists
                    if type(key_to) == list:
                        for key in key_to:
                            # continue if final key was set in update_data
                            if key in updating_data:
                                continue

                            # continue if source key not exist or value is None
                            value = source_data.get(key_from)
                            if value is None:
                                continue

                            self.log.debug(
                                "-- changing key {} to {}".format(
                                    key_from,
                                    key
                                )
                            )

                            updating_data[key] = value
                    else:
                        if key_to in source_data:
                            continue

                        # continue if final key was set in update_data
                        if key_to in updating_data:
                            continue

                        # continue if source key not exist or value is None
                        value = source_data.get(key_from)
                        if value is None:
                            continue

                        self.log.debug(
                            "-- changing key {} to {}".format(key_from, key_to)
                        )
                        updating_data[key_to] = value

                # Pop out old keys from entity
                is_obsolete = False
                for key in self.keys_to_change:
                    if key not in source_data:
                        continue
                    is_obsolete = True
                    source_data.pop(key)

                # continue if there is nothing to change
                if not is_obsolete and not updating_data:
                    self.log.debug("-- nothing to change")
                    continue

                source_data.update(updating_data)

                self.db_con.update_many(
                    {"_id": _entity["_id"]},
                    {"$set": {"data": source_data}}
                )

        self.db_con.uninstall()

        if interface_messages:
            self.show_interface_from_dict(
                messages=interface_messages,
                title="Errors during remapping attributes",
                event=event
            )

        return True

    def show_interface_from_dict(self, event, messages, title=""):
        items = []

        for key, value in messages.items():
            if not value:
                continue
            subtitle = {'type': 'label', 'value': '# {}'.format(key)}
            items.append(subtitle)
            if isinstance(value, list):
                for item in value:
                    message = {
                        'type': 'label', 'value': '<p>{}</p>'.format(item)
                    }
                    items.append(message)
            else:
                message = {'type': 'label', 'value': '<p>{}</p>'.format(value)}
                items.append(message)

        self.show_interface(items=items, title=title, event=event)

def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    AttributesRemapper(session, plugins_presets).register()
