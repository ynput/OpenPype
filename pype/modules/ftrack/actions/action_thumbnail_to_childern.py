import json
from pype.modules.ftrack.lib import BaseAction, statics_icon


class ThumbToChildren(BaseAction):
    '''Custom action.'''

    # Action identifier
    identifier = 'thumb.to.children'
    # Action label
    label = 'Thumbnail'
    # Action variant
    variant = " to Children"
    # Action icon
    icon = statics_icon("ftrack", "action_icons", "Thumbnail.svg")

    def discover(self, session, entities, event):
        ''' Validation '''

        if (len(entities) != 1 or entities[0].entity_type in ['Project']):
            return False

        return True

    def launch(self, session, entities, event):
        '''Callback method for action.'''

        userId = event['source']['user']['id']
        user = session.query('User where id is ' + userId).one()

        job = session.create('Job', {
            'user': user,
            'status': 'running',
            'data': json.dumps({
                'description': 'Push thumbnails to Childrens'
            })
        })
        session.commit()
        try:
            for entity in entities:
                thumbid = entity['thumbnail_id']
                if thumbid:
                    for child in entity['children']:
                        child['thumbnail_id'] = thumbid

            # inform the user that the job is done
            job['status'] = 'done'
        except Exception as exc:
            session.rollback()
            # fail the job if something goes wrong
            job['status'] = 'failed'
            raise exc
        finally:
            session.commit()

        return {
            'success': True,
            'message': 'Created job for updating thumbnails!'
        }


def register(session, plugins_presets={}):
    '''Register action. Called when used as an event plugin.'''

    ThumbToChildren(session, plugins_presets).register()
