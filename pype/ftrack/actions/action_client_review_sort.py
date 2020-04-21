from pype.ftrack import BaseAction


class ClientReviewSort(BaseAction):
    '''Custom action.'''

    #: Action identifier.
    identifier = 'client.review.sort'

    #: Action label.
    label = 'Sort Review'

    def discover(self, session, entities, event):
        ''' Validation '''

        if (len(entities) == 0 or entities[0].entity_type != 'ReviewSession'):
            return False

        return True

    def launch(self, session, entities, event):

        entity = entities[0]

        # Get all objects from Review Session and all 'sort order' possibilities
        obj_list = []
        sort_order_list = []
        for obj in entity['review_session_objects']:
            obj_list.append(obj)
            sort_order_list.append(obj['sort_order'])

        # Sort criteria
        obj_list = sorted(obj_list, key=lambda k: k['version'])
        obj_list = sorted(
            obj_list, key=lambda k: k['asset_version']['task']['name']
        )
        obj_list = sorted(obj_list, key=lambda k: k['name'])

        # Set 'sort order' to sorted list, so they are sorted in Ftrack also
        for i in range(len(obj_list)):
            obj_list[i]['sort_order'] = sort_order_list[i]

        session.commit()

        return {
            'success': True,
            'message': 'Client Review sorted!'
        }


def register(session, plugins_presets={}):
    '''Register action. Called when used as an event plugin.'''

    ClientReviewSort(session, plugins_presets).register()
