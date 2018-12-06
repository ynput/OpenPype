import ftrack_api
from utils import print_entity_head
#
session = ftrack_api.Session()

# ----------------------------------


def thumbnail_updates(event):
    '''Update thumbnails automatically'''

    # start of event procedure ----------------------------------
    for entity in event['data'].get('entities', []):

        # update created task thumbnail with first parent thumbnail
        if entity['entityType'] == 'task' and entity['action'] == 'add':

            print "\n\nevent script: {}".format(__file__)
            print_entity_head.print_entity_head(entity, session)

            task = session.get('TypedContext', entity['entityId'])
            parent = task['parent']

            if parent.get('thumbnail') and not task.get('thumbnail'):
                task['thumbnail'] = parent['thumbnail']
                print '>>> Updated thumbnail on [ %s/%s ]'.format(
                    parent['name'], task['name'])

        # Update task thumbnail from published version
        if entity['entityType'] == 'assetversion' and entity['action'] == 'encoded':

            version = session.get('AssetVersion', entity['entityId'])
            thumbnail = version.get('thumbnail')
            task = version['task']

            if thumbnail:
                task['thumbnail'] = thumbnail
                task['parent']['thumbnail'] = thumbnail
                print '>>> Updating thumbnail for task and shot [ {} ]'.format(
                    task['name'])

        session.commit()
    # end of event procedure ----------------------------------
