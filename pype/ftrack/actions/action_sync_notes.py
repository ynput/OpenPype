import os
import sys
import time
import datetime
import requests
import tempfile

from pype.vendor import ftrack_api
from pype.ftrack import BaseAction
from pype.ftrack.lib.custom_db_connector import DbConnector, ClientSession


class SynchronizeNotes(BaseAction):
    #: Action identifier.
    identifier = 'sync.notes'
    #: Action label.
    label = 'Synchronize Notes'
    #: Action description.
    description = 'Synchronize notes from one Ftrack to another'
    #: roles that are allowed to register this action
    role_list = ['Pypeclub']

    db_con = DbConnector(
        mongo_url=os.environ["AVALON_MONGO"],
        database_name='customDatabase',
        table_name='notesTable'
    )

    id_key_src = 'fridge_ftrackID'
    id_key_dst = 'kredenc_ftrackID'
    date_store_key = 'last_stored_asset_version'

    def discover(self, session, entities, event):
        ''' Validation '''
        if len(entities) == 0:
            return False

        for entity in entities:
            if entity.entity_type.lower() != 'assetversion':
                return False

        return True

    def launch(self, session, entities, event):

        self.session_source = ftrack_api.Session(
            server_url='',
            api_key='',
            api_user='',
            auto_connect_event_hub=True
        )

        self.session_for_components = ftrack_api.Session(
            server_url=session.server_url,
            api_key=session.api_key,
            api_user=session.api_user,
            auto_connect_event_hub=True
        )

        self.user = self.session_for_components.query(
            'User where username is "{}"'.format(self.session.api_user)
        ).one()

        self.db_con.install()

        missing_id_entities = []
        to_sync_data = []
        for dst_entity in entities:
            # Ignore entities withoud stored id from second ftrack
            from_id = dst_entity['custom_attributes'].get(self.id_key_src)
            if not from_id:
                missing_id_entities.append(dst_entity.get('name', dst_entity))
                continue

            to_sync_data.append((dst_entity.entity_type, dst_entity['id']))

        for dst_entity_data in to_sync_data:
            av_query = 'AssetVersion where id is "{}"'.format(from_id)
            src_entity = self.session_source.query(av_query).one()
            src_notes = src_entity['notes']
            self.sync_notes(src_notes, dst_entity_data)

        self.db_con.uninstall()

        if missing_id_entities:
            self.log.info('Entities without Avalon ID:')
            self.log.info(missing_id_entities)

        return True

    def sync_notes(self, src_notes, dst_entity_data):
        # Sort notes by date time
        src_notes = sorted(src_notes, key=lambda note: note['date'])

        for src_note in src_notes:
            # Find if exists in DB
            db_note_entity = self.db_con.find_one({
                self.id_key_src: src_note['id']
            })
            # WARNING: expr `if not db_note_entity:` does not work!

            if db_note_entity is None:
                    # Create note if not found in DB
                dst_note_id = self.create_note(
                    src_note, dst_entity_data
                )
                # Add references to DB for next sync
                item = {
                    self.id_key_dst: dst_note_id,
                    self.id_key_src: src_note['id'],
                    'content': src_note['content'],
                    'entity_type': 'Note',
                    'sync_date': str(datetime.date.today())
                }
                self.db_con.insert_one(item)
            else:
                dst_note_id = db_note_entity[self.id_key_dst]

            replies = src_note.get('replies')
            if not replies:
                continue

            self.sync_notes(replies, ('Note', dst_note_id))

    def create_note(self, src_note, dst_entity_data):
        # dst_entity_data - tuple(entity type, entity id)
        dst_entity = self.session.query(
            '{} where id is "{}"'.format(*dst_entity_data)
        ).one()

        is_reply = False
        if dst_entity.entity_type.lower() != 'note':
            # Category
            category = None
            cat = src_note['category']
            if cat:
                cat_name = cat['name']
                category = self.session.query(
                    'NoteCategory where name is "{}"'.format(cat_name)
                ).first()

            new_note = dst_entity.create_note(
                src_note['content'], self.user, category=category
            )
        else:
            new_note = dst_entity.create_reply(
                src_note['content'], self.user
            )
            is_reply = True

        # TODO Should we change date to match source Ftrack?
        # new_note['data'] = src_note['date']

        self.session.commit()
        new_note_id = new_note['id']

        # Components
        if src_note['note_components']:
            self.reupload_components(src_note, new_note_id)

        # Bug in ftrack_api, when reply is added session must be reset
        if is_reply:
            self.session.reset()
            time.sleep(0.2)

        return new_note_id

    def reupload_components(self, src_note, dst_note_id):
        # Download and collect source components
        src_server_location = self.session_source.query(
            'Location where name is "ftrack.server"'
        ).one()

        temp_folder = tempfile.mkdtemp('note_components')

        #download and store path to upload
        paths_to_upload = []
        count = 0
        for note_component in src_note['note_components']:
            count +=1
            download_url = src_server_location.get_url(
                note_component['component']
            )

            file_name = '{}{}{}'.format(
                str(src_note['date'].format('YYYYMMDDHHmmss')),
                "{:0>3}".format(count),
                note_component['component']['file_type']
            )
            path = os.path.sep.join([temp_folder, file_name])

            self.download_file(download_url, path)
            paths_to_upload.append(path)

        # Create downloaded components and add to note
        dst_server_location = self.session_for_components.query(
            'Location where name is "ftrack.server"'
        ).one()

        for path in paths_to_upload:
            component = self.session_for_components.create_component(
                path,
                data={'name': 'My file'},
                location=dst_server_location
            )

            # Attach the component to the note.
            self.session_for_components.create(
                'NoteComponent',
                {'component_id': component['id'], 'note_id': dst_note_id}
            )

        self.session_for_components.commit()

    def download_file(self, url, path):
        r = requests.get(url, stream=True).content
        with open(path, 'wb') as f:
            f.write(r)


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    SynchronizeNotes(session).register()
