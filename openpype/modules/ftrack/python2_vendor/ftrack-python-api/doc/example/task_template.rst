..
    :copyright: Copyright (c) 2017 ftrack

.. _example/task_template:

***************************
Working with Task Templates
***************************

Task templates can help you organize your workflows by building a collection
of tasks to be applied for specific contexts. They can be applied to all `Context`
objects for example Project, Sequences, Shots, etc...

Query task templates
=======================

Retrive all task templates and there tasks for a project::

    project = session.query('Project').first()

    for task_template in project['project_schema']['task_templates']:
        print('\ntask template: {0}'.format(
            task_template['name']
        ))

        for task_type in [t['task_type'] for t in task_template['items']]:
            print('\ttask type: {0}'.format(
                task_type['name']
            ))



"Apply" a task template
=======================
Create all tasks in a random task template directly under the project::


    project = session.query('Project').first()

    task_template = random.choice(
        project['project_schema']['task_templates']
    )

    for task_type in [t['task_type'] for t in task_template['items']]:
        session.create(
            'Task', {
                'name': task_type['name'],
                'type': task_type,
                'parent': project
            }
        )

    session.commit()



