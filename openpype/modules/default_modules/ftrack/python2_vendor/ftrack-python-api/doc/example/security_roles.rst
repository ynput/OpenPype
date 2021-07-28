..
    :copyright: Copyright (c) 2017 ftrack

.. _example/security_roles:

*********************************
Working with user security roles
*********************************

.. currentmodule:: ftrack_api.session

The API exposes `SecurityRole` and `UserSecurityRole` that can be used to
specify who should have access to certain data on different projects.

List all available security roles like this::

    security_roles = session.query(
        'select name from SecurityRole where type is "PROJECT"'
    )

.. note::

    We only query for project roles since those are the ones we can add to a
    user for certain projects. Other types include API and ASSIGNED. Type API
    can only be added to global API keys, which is currently not supported via
    the api and type ASSIGNED only applies to assigned tasks.

To get all security roles from a user we can either use relations like this::

    for user_security_role in user['user_security_roles']:
        if user_security_role['is_all_projects']:
            result_string = 'all projects'
        else:
            result_string = ', '.join(
                [project['full_name'] for project in user_security_role['projects']]
            )

        print 'User has security role "{0}" which is valid on {1}.'.format(
            user_security_role['security_role']['name'],
            result_string
        )

or query them directly like this::

    user_security_roles = session.query(
        'UserSecurityRole where user.username is "{0}"'.format(session.api_user)
    ).all()

User security roles can also be added to a user for all projects like this::

    project_manager_role = session.query(
        'SecurityRole where name is "Project Manager"'
    ).one()

    session.create('UserSecurityRole', {
        'is_all_projects': True,
        'user': user,
        'security_role': project_manager_role
    })
    session.commit()

or for certain projects only like this::

    projects = session.query(
        'Project where full_name is "project1" or full_name is "project2"'
    ).all()[:]

    session.create('UserSecurityRole', {
        'user': user,
        'security_role': project_manager_role,
        'projects': projects
    })
    session.commit()
