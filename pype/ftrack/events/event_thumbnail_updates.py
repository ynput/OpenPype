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
                        parent['name'], task['name']
                    ))

            # Update task thumbnail from published version
            # if (entity['entityType'] == 'assetversion' and
            #         entity['action'] == 'encoded'):
            if (
                entity['entityType'] == 'assetversion'
                and 'thumbid' in (entity.get('keys') or [])
            ):

                version = session.get('AssetVersion', entity['entityId'])
                thumbnail = version.get('thumbnail')
                if thumbnail:
                    parent = version['asset']['parent']
                    task = version['task']
                    parent['thumbnail_id'] = version['thumbnail_id']
                    if parent.entity_type.lower() == "project":
                        name = parent["full_name"]
                    else:
                        name = parent["name"]
                    msg = '>>> Updating thumbnail for shot [ {} ]'.format(name)

                    if task:
                        task['thumbnail_id'] = version['thumbnail_id']
                        msg += " and task [ {} ]".format(task["name"])

                    self.log.info(msg)

            session.commit()


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''

    ThumbnailEvents(session, plugins_presets).register()
