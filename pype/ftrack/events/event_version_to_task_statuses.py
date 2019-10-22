from pype.vendor import ftrack_api
from pype.ftrack import BaseEvent


class VersionToTaskStatus(BaseEvent):

    def launch(self, session, event):
        '''Propagates status from version to task when changed'''
        session.commit()

        # start of event procedure ----------------------------------
        for entity in event['data'].get('entities', []):
            # Filter non-assetversions
            if (
                entity['entityType'] == 'assetversion' and
                'statusid' in (entity.get('keys') or [])
            ):

                version = session.get('AssetVersion', entity['entityId'])
                try:
                    version_status = session.get(
                        'Status', entity['changes']['statusid']['new']
                    )
                except Exception:
                    continue
                task_status = version_status
                task = version['task']
                self.log.info('>>> version status: [ {} ]'.format(
                    version_status['name']))

                status_to_set = None
                # Filter to versions with status change to "render complete"
                if version_status['name'].lower() == 'reviewed':
                    status_to_set = 'Change requested'

                if version_status['name'].lower() == 'approved':
                    status_to_set = 'Complete'

                self.log.info(
                    '>>> status to set: [ {} ]'.format(status_to_set))

                if status_to_set is not None:
                    query = 'Status where name is "{}"'.format(status_to_set)
                    try:
                        task_status = session.query(query).one()
                    except Exception:
                        self.log.info(
                            '!!! status was not found in Ftrack [ {} ]'.format(
                                status_to_set
                        ))
                        continue

                # Proceed if the task status was set
                if task_status is not None:
                    # Get path to task
                    path = task['name']
                    for p in task['ancestors']:
                        path = p['name'] + '/' + path

                    # Setting task status
                    try:
                        task['status'] = task_status
                        session.commit()
                    except Exception as e:
                        self.log.warning('!!! [ {} ] status couldnt be set:\
                            [ {} ]'.format(path, e))
                    else:
                        self.log.info('>>> [ {} ] updated to [ {} ]'.format(
                            path, task_status['name']))


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''

    VersionToTaskStatus(session, plugins_presets).register()
