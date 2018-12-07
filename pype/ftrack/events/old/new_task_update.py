# import ftrack_api as local session
import ftrack_api
import operator
from utils import print_entity_head
#
session = ftrack_api.Session()

# ----------------------------------


def new_task_update(event):
    ''' Set next task to ready when previous task is \
    completed. '''

    # start of event procedure ----------------------------------
    def get_next_task(task):
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

    for entity in event['data'].get('entities', []):

        if (entity['entityType'] == 'task' and 'statusid' in entity['keys']):

            print "\n\nevent script: {}".format(__file__)
            print_entity_head.print_entity_head(entity, session)

            task = session.get('Task', entity['entityId'])

            status = session.get('Status',
                                 entity['changes']['statusid']['new'])
            state = status['state']['name']

            next_task = get_next_task(task)

            # Setting next task to NOT STARTED, if on NOT READY
            if next_task and state == 'Done':
                if next_task['status']['name'].lower() == 'not ready':

                    # Get path to task
                    path = task['name']
                    for p in task['ancestors']:
                        path = p['name'] + '/' + path

                    # Setting next task status
                    try:
                        status_to_set = session.query(
                            'Status where name is "{}"'.format('Ready')).one()
                        next_task['status'] = status_to_set
                    except Exception as e:
                        print '!!! [ {} ] status couldnt be set: [ {} ]'.format(
                            path, e)
                    else:
                        print '>>> [ {} ] updated to [ Ready ]'.format(path)

            session.commit()
    # end of event procedure ----------------------------------
