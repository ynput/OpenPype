..
    :copyright: Copyright (c) 2015 ftrack

.. _example/assignments_and_allocations:

****************************************
Working with assignments and allocations
****************************************

.. currentmodule:: ftrack_api.session

The API exposes `assignments` and `allocations` relationships on objects in
the project hierarchy. You can use these to retrieve the allocated or assigned
resources, which can be either groups or users. 

Allocations can be used to allocate users or groups to a project team, while
assignments are more explicit and is used to assign users to tasks. Both
assignment and allocations are modelled as `Appointment` objects, with a
`type` attribute indicating the type of the appoinment.

The following example retrieves all users part of the project team::

    # Retrieve a project
    project = session.query('Project').first()

    # Set to hold all users part of the project team
    project_team = set()

    # Add all allocated groups and users
    for allocation in project['allocations']:

        # Resource may be either a group or a user
        resource = allocation['resource']

        # If the resource is a group, add its members
        if isinstance(resource, session.types['Group']):
            for membership in resource['memberships']:
                user = membership['user']
                project_team.add(user)

        # The resource is a user, add it.
        else:
            user = resource
            project_team.add(user)

The next example shows how to assign the current user to a task::

    # Retrieve a task and the current user
    task = session.query('Task').first()
    current_user = session.query(
        u'User where username is {0}'.format(session.api_user)
    ).one()

    # Create a new Appointment of type assignment.
    session.create('Appointment', {
        'context': task,
        'resource': current_user,
        'type': 'assignment'
    })

    # Finally, persist the new assignment
    session.commit()

To list all users assigned to a task, see the following example::

    task = session.query('Task').first()
    users = session.query(
        'select first_name, last_name from User '
        'where assignments any (context_id = "{0}")'.format(task['id'])
    )
    for user in users:
        print user['first_name'], user['last_name']

To list the current user's assigned tasks, see the example below::

    assigned_tasks = session.query(
        'select link from Task '
        'where assignments any (resource.username = "{0}")'.format(session.api_user)
    )
    for task in assigned_tasks:
        print u' / '.join(item['name'] for item in task['link'])

