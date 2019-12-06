from pype.ftrack import BaseEvent
from pypeapp import config


class VersionToTaskStatus(BaseEvent):

    default_status_mapping = {
        'reviewed': 'Change requested',
        'approved': 'Complete'
    }

    def launch(self, session, event):
        '''Propagates status from version to task when changed'''

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

                version_name_low = version_status['name'].lower()

                status_mapping = (
                    config.get_presets()
                    .get("ftrack", {})
                    .get("ftrack_config", {})
                    .get("status_version_to_task")
                ) or self.default_status_mapping
                status_to_set = status_mapping.get(version_name_low)

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
                            )
                        )
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
                        session.rollback()
                        self.log.warning('!!! [ {} ] status couldnt be set:\
                            [ {} ]'.format(path, e))
                        session.rollback()
                    else:
                        self.log.info('>>> [ {} ] updated to [ {} ]'.format(
                            path, task_status['name']))


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''

    VersionToTaskStatus(session, plugins_presets).register()
