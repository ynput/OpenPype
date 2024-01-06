import logging

import ftrack_api

import os

class HornetNoteEditConform(object):
    '''Custom action.'''

    label = 'Ready for Edit'
    identifier = 'hornet.note.editorial.conform'
    description = 'Action to Requesting a Editorial New Version for Editorial Cut'

    def __init__(self, session):
        '''Initialise action.'''
        super(HornetNoteEditConform, self).__init__()
        self.session = session
        self.logger = logging.getLogger(
            __name__ + '.' + self.__class__.__name__
        )

    def register(self):
        '''Register action.'''
        self.session.event_hub.subscribe(
            'topic=ftrack.action.discover and source.user.username={0}'.format(
                self.session.api_user
            ),
            self.discover
        )

        self.session.event_hub.subscribe(
            'topic=ftrack.action.launch and data.actionIdentifier={0} and '
            'source.user.username={1}'.format(
                self.identifier,
                self.session.api_user
            ),
            self.launch
        )

    def discover(self, event):
        '''Return action config if triggered on a single asset version.'''
        data = event['data']

        '''If selection contains more than one item return early since
        this action can only handle a single version.'''

        selection = data.get('selection', [])
        self.logger.info('Got selection: {0}'.format(selection))
        if (
            len(selection) != 1 or
            selection[0]['entityType'] != 'assetversion'
        ):
            return

        return {
            'items': [{
                'label': self.label,
                'description': self.description,
                'actionIdentifier': self.identifier
            }]
        }

    def launch(self, event):
        '''Callback method for custom action.'''
        selection = event['data'].get('selection', [])

        for entity in selection:

            version = self.session.get(
                'AssetVersion', entity['entityId']
            )
            task_id = self.get_edit_task_id(version)
            body = self.get_assetversion_path(version)
            # Generate the note
            self.add_editorial_note(task_id, body)

        return {
            'success': True,
            'message': 'Ran my custom action successfully!'
        }

    def get_edit_task_id(self, assetversion_obj):
        #get the shot
        shot = (assetversion_obj['task']['parent'])
        for i in shot['children'] :
            # find the edit task under the shot
            if i['name'] == 'edit' :
                return i['id']

    def get_assetversion_path(self, assetversion_obj)  :
        '''
        find 'jpg', 'exr', 'ftrackreview-mp4_src'
        '''
        body = ''
        # get file_path
        for i in (assetversion_obj['components']):
            file_type= i['name']
            if file_type in ['jpg', 'exr', 'ftrackreview-mp4_src'] :
                win_path = i['component_locations'][0]['resource_identifier']
                body += '\n'
                body = file_type
                body += '\n'
                '''
                P:\projects\internalTesting\test_jyoo_ftrack\sequences\rnd010\publish\image\imageReference\v003\rnd010_imageReference_v003.jpg

                Volumes\production\projects\test_jyoo_ftrack\sequences\rnd010\publish\image\imageReference\v003\rnd010_imageReference_v003.jpg
                '''
                proj = self.session.get('Project', assetversion_obj['project_id'])
                if win_path.startswith('P:\projects'):
                    split = win_path.split(proj['name'])
                    mac_path = ('Volumes\\production\\projects\\' + proj['name'] + split[1])
                    body += mac_path
                else:
                    body += win_path
        return body

    def add_editorial_note(self, task_id, body):
        '''
        #this is the test id
        '2116a15d-e878-46e4-8441-8649427bc2ee'
        This creates a new note of a task, should be the 'edit' task on a shot.
        # todo missing
        '''
        session = ftrack_api.Session(
                server_url=os.environ['FTRACK_SERVER'],
                api_key=os.environ['FTRACK_API_KEY'],
                api_user=os.environ['FTRACK_API_USER'],
        )

        task = session.get('Task', task_id)
        '''
        Creating a new note
        '''
        CONTENT = 'New Version for Editorial : \n'
        CONTENT += body
        user = session.query('User where username is "{0}"'.format(os.environ['FTRACK_API_USER'])).one()
        edit_group = session.query('Group where name is "Editorial Team"').first()
        print(user['email'])
        print(user)

        # Create note using the helper method.
        note = task.create_note(CONTENT, author=user, recipients=[edit_group])
        note['is_todo'] = True
        # note['custom_attributes']['label'] = 'Edit WIP Conform'  # LABEL SETTING IS NOT WORKING
        session.commit()
        print(note)

def register(session, **kw):
    '''Register plugin.'''

    '''
    Validate that session is an instance of ftrack_api.Session. If not, assume that register is being called from an incompatible API and return without doing anything.
    '''
    if not isinstance(session, ftrack_api.Session):
        return

    action = HornetNoteEditConform(session)
    action.register()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session()
    register(session)

    '''Wait for events.'''
    session.event_hub.wait()
