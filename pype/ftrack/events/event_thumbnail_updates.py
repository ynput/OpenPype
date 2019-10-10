from pype.vendor import ftrack_api
from pype.ftrack import BaseEvent


class ThumbnailEvents(BaseEvent):

    def launch(self, session, event):
        '''just a testing event'''

        # self.log.info(event)
        # start of event procedure ----------------------------------
        for entity in event['data'].get('entities', []):

            # update created task thumbnail with first parent thumbnail
            if entity['entityType'] == 'task' and entity['action'] == 'add':

                task = session.get('TypedContext', entity['entityId'])
                parent = task['parent']

                if parent.get('thumbnail') and not task.get('thumbnail'):
                    task['thumbnail'] = parent['thumbnail']
                    self.log.info('>>> Updated thumbnail on [ %s/%s ]'.format(
                        parent['name'], task['name']))

            # Update task thumbnail from published version
            # if (entity['entityType'] == 'assetversion' and
            #         entity['action'] == 'encoded'):
            if (
                entity['entityType'] == 'assetversion'
                and 'thumbid' in entity.get('keys', [])
            ):

                version = session.get('AssetVersion', entity['entityId'])
                thumbnail = version.get('thumbnail')
                task = version['task']

                if thumbnail:
                    task['thumbnail'] = thumbnail
                    task['parent']['thumbnail'] = thumbnail
                    self.log.info('>>> Updating thumbnail for task and shot\
                        [ {} ]'.format(task['name']))

            session.commit()

        pass


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''
    if not isinstance(session, ftrack_api.session.Session):
        return

    ThumbnailEvents(session, plugins_presets).register()
