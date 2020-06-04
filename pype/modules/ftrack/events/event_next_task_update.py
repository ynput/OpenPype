import ftrack_api
from pype.modules.ftrack import BaseEvent
import operator


class NextTaskUpdate(BaseEvent):

    def get_next_task(self, task, session):
        parent = task['parent']
        # tasks = parent['tasks']
        tasks = parent['children']

        def sort_types(types):
            data = {}
            for t in types:
                data[t] = t.get('sort')

            data = sorted(data.items(), key=operator.itemgetter(1))
            results = []
            for item in data:
                results.append(item[0])
            return results

        types_sorted = sort_types(session.query('Type'))
        next_types = None
        for t in types_sorted:
            if t['id'] == task['type_id']:
                next_types = types_sorted[(types_sorted.index(t) + 1):]

        for nt in next_types:
            for t in tasks:
                if nt['id'] == t['type_id']:
                    return t

        return None

    def launch(self, session, event):
        '''Propagates status from version to task when changed'''

        # self.log.info(event)
        # start of event procedure ----------------------------------

        for entity in event['data'].get('entities', []):
            changes = entity.get('changes', None)
            if changes is None:
                continue
            statusid_changes = changes.get('statusid', {})
            if (
                entity['entityType'] != 'task' or
                'statusid' not in (entity.get('keys') or []) or
                statusid_changes.get('new', None) is None or
                statusid_changes.get('old', None) is None
            ):
                continue

            task = session.get('Task', entity['entityId'])

            status = session.get('Status',
                                 entity['changes']['statusid']['new'])
            state = status['state']['name']

            next_task = self.get_next_task(task, session)

            # Setting next task to Ready, if on NOT READY
            if next_task and state == 'Done':
                if next_task['status']['name'].lower() == 'not ready':

                    # Get path to task
                    path = task['name']
                    for p in task['ancestors']:
                        path = p['name'] + '/' + path

                    # Setting next task status
                    try:
                        query = 'Status where name is "{}"'.format('Ready')
                        status_to_set = session.query(query).one()
                        next_task['status'] = status_to_set
                        session.commit()
                        self.log.info((
                            '>>> [ {} ] updated to [ Ready ]'
                        ).format(path))
                    except Exception as e:
                        session.rollback()
                        self.log.warning((
                            '!!! [ {} ] status couldnt be set: [ {} ]'
                        ).format(path, str(e)), exc_info=True)


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''

    NextTaskUpdate(session, plugins_presets).register()
