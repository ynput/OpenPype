..
    :copyright: Copyright (c) 2015 ftrack

.. currentmodule:: ftrack_api.session

.. _example/note:

***********
Using notes
***********

Notes can be written on almost all levels in ftrack. To retrieve notes on an
entity you can either query them or use the relation called `notes`::
    
    task = session.query('Task').first()
    
    # Retrieve notes using notes property.
    notes_on_task = task['notes']

    # Or query them.
    notes_on_task = session.query('Note where parent_id is "{}"'.format(
        task['id']
    ))

.. note::

    It's currently not possible to use the `parent` property when querying
    notes or to use the `parent` property on notes::

        task = session.query('Task').first()

        # This won't work in the current version of the API.
        session.query('Note where parent.id is "{}"'.format(
            task['id']
        ))

        # Neither will this.
        parent_of_note = note['parent']

To create new notes you can either use the helper method called
:meth:`~ftrack_api.entity.note.CreateNoteMixin.create_note` on any entity that
can have notes or use :meth:`Session.create` to create them manually::

    user = session.query('User').first()

    # Create note using the helper method.
    note = task.create_note('My new note', author=user)

    # Manually create a note
    note = session.create('Note', {
        'content': 'My new note',
        'author': user
    })
    
    task['notes'].append(note)

Replying to an existing note can also be done with a helper method or by
using :meth:`Session.create`::

    # Create using helper method.
    first_note_on_task = task['notes'][0]
    first_note_on_task.create_reply('My new reply on note', author=user)

    # Create manually
    reply = session.create('Note', {
        'content': 'My new note',
        'author': user
    })
    
    first_note_on_task.replies.append(reply)

Notes can have labels. Use the label argument to set labels on the
note using the helper method::

    label = session.query(
        'NoteLabel where name is "External Note"'
    ).first()

    note = task.create_note(
        'New note with external category', author=user, labels=[label]
    )

Or add labels to notes when creating a note manually::

    label = session.query(
        'NoteLabel where name is "External Note"'
    ).first()

    note = session.create('Note', {
        'content': 'New note with external category',
        'author': user
    })

    session.create('NoteLabelLink', {
        'note_id': note['id],
        'label_id': label['id']
    })

    task['notes'].append(note)

.. note::

    Support for labels on notes was added in ftrack server version 4.3. For
    older versions of the server, NoteCategory can be used instead.

To specify a category when creating a note simply pass a `NoteCategory` instance
to the helper method::

    category = session.query(
        'NoteCategory where name is "External Note"'
    ).first()

    note = task.create_note(
        'New note with external category', author=user, category=category
    )

When writing notes you might want to direct the note to someone. This is done
by adding users as recipients. If a user is added as a recipient the user will
receive notifications and the note will be displayed in their inbox.

To add recipients pass a list of user or group instances to the helper method::

    john = session.query('User where username is "john"').one()
    animation_group = session.query('Group where name is "Animation"').first()

    note = task.create_note(
        'Note with recipients', author=user, recipients=[john, animation_group]
    )

Attachments
===========

Note attachments are files that are attached to a note. In the ftrack web
interface these attachments appears next to the note and can be downloaded by
the user.

To get a note's attachments through the API you can use the `note_components`
relation and then use the ftrack server location to get the download URL::

    server_location = session.query(
        'Location where name is "ftrack.server"'
    ).one()

    for note_component in note['note_components']:
        print 'Download URL: {0}'.format(
            server_location.get_url(note_component['component'])
        )

To add an attachment to a note you have to add it to the ftrack server location
and create a `NoteComponent`::

    server_location = session.query(
        'Location where name is "ftrack.server"'
    ).one()    

    # Create component and name it "My file".
    component = session.create_component(
        '/path/to/file',
        data={'name': 'My file'},
        location=server_location
    )

    # Attach the component to the note.
    session.create(
        'NoteComponent',
        {'component_id': component['id'], 'note_id': note['id']}
    )

    session.commit()
