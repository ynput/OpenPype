# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import ftrack_api
import ftrack_api.inspection


def test_create_reply(session, new_note, user, unique_name):
    '''Create reply to a note.'''
    reply_text = 'My reply on note'
    new_note.create_reply(reply_text, user)

    session.commit()

    assert len(new_note['replies']) == 1

    assert reply_text == new_note['replies'][0]['content']


def test_create_note_on_entity(session, new_task, user, unique_name):
    '''Create note attached to an entity.'''
    note = new_task.create_note(unique_name, user)
    session.commit()

    session.reset()
    retrieved_task = session.get(*ftrack_api.inspection.identity(new_task))
    assert len(retrieved_task['notes']) == 1
    assert (
        ftrack_api.inspection.identity(retrieved_task['notes'][0])
        == ftrack_api.inspection.identity(note)
    )


def test_create_note_on_entity_specifying_recipients(
    session, new_task, user, unique_name, new_user
):
    '''Create note with specified recipients attached to an entity.'''
    recipient = new_user
    note = new_task.create_note(unique_name, user, recipients=[recipient])
    session.commit()

    session.reset()
    retrieved_note = session.get(*ftrack_api.inspection.identity(note))

    # Note: The calling user is automatically added server side so there will be
    # 2 recipients.
    assert len(retrieved_note['recipients']) == 2
    specified_recipient_present = False
    for entry in retrieved_note['recipients']:
        if entry['resource_id'] == recipient['id']:
            specified_recipient_present = True
            break

    assert specified_recipient_present


def test_create_note_on_entity_specifying_category(
    session, new_task, user, unique_name
):
    '''Create note with specified category attached to an entity.'''
    category = session.query('NoteCategory').first()
    note = new_task.create_note(unique_name, user, category=category)
    session.commit()

    session.reset()
    retrieved_note = session.get(*ftrack_api.inspection.identity(note))
    assert retrieved_note['category']['id'] == category['id']
