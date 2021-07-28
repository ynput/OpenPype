# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack


def test_add_remove_and_query_scopes_for_tasks(session, new_task, new_scope):
    '''Add, remove and query scopes for task.'''
    query_string = 'Task where scopes.name is {0}'.format(new_scope['name'])
    tasks = session.query(query_string)

    assert len(tasks) == 0

    new_task['scopes'].append(new_scope)
    session.commit()

    tasks = session.query(query_string)

    assert len(tasks) == 1 and tasks[0] == new_task

    new_task['scopes'].remove(new_scope)
    session.commit()

    tasks = session.query(query_string)

    assert len(tasks) == 0
