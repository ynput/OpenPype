..
    :copyright: Copyright (c) 2015 ftrack

.. _example/project:

*********************
Working with projects
*********************

.. currentmodule:: ftrack_api.session

Creating a project
==================

A project with sequences, shots and tasks can be created in one single
transaction. Tasks need to have a type and status set on creation based on the
project schema::

    import uuid

    # Create a unique name for the project.
    name = 'projectname_{0}'.format(uuid.uuid1().hex)

    # Naively pick the first project schema. For this example to work the
    # schema must contain `Shot` and `Sequence` object types.
    project_schema = session.query('ProjectSchema').first()

    # Create the project with the chosen schema.
    project = session.create('Project', {
        'name': name,
        'full_name': name + '_full',
        'project_schema': project_schema
    })

    # Retrieve default types.
    default_shot_status = project_schema.get_statuses('Shot')[0]
    default_task_type = project_schema.get_types('Task')[0]
    default_task_status = project_schema.get_statuses(
        'Task', default_task_type['id']
    )[0]

    # Create sequences, shots and tasks.
    for sequence_number in range(1, 5):
        sequence = session.create('Sequence', {
            'name': 'seq_{0}'.format(sequence_number),
            'parent': project
        })

        for shot_number in range(1, 5):
            shot = session.create('Shot', {
                'name': '{0}0'.format(shot_number).zfill(3),
                'parent': sequence,
                'status': default_shot_status
            })

            for task_number in range(1, 5):
                session.create('Task', {
                    'name': 'task_{0}'.format(task_number),
                    'parent': shot,
                    'status': default_task_status,
                    'type': default_task_type
                })

    # Commit all changes to the server.
    session.commit()
