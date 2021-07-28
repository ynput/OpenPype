..
    :copyright: Copyright (c) 2015 ftrack

.. _example/review_session:

*********************
Using review sessions
*********************

.. currentmodule:: ftrack_api.session

Client review sessions can either be queried manually or by using a project
instance.

.. code-block:: python

    review_sessions = session.query(
        'ReviewSession where name is "Weekly review"'
    )
    
    project_review_sessions = project['review_sessions']

To create a new review session on a specific project use :meth:`Session.create`.

.. code-block:: python

    review_session = session.create('ReviewSession', {
        'name': 'Weekly review',
        'description': 'See updates from last week.',
        'project': project
    })

To add objects to a review session create them using
:meth:`Session.create` and reference a review session and an asset version.

.. code-block:: python

    review_session = session.create('ReviewSessionObject', {
        'name': 'Compositing',
        'description': 'Fixed shadows.',
        'version': 'Version 3',
        'review_session': review_session,
        'asset_version': asset_version
    })

To list all objects in a review session.

.. code-block:: python

    review_session_objects = review_session['review_session_objects']

Listing and adding collaborators to review session can be done using 
:meth:`Session.create` and the `review_session_invitees` relation on a 
review session.

.. code-block:: python

    invitee = session.create('ReviewSessionInvitee', {
        'name': 'John Doe',
        'email': 'john.doe@example.com',
        'review_session': review_session
    })
    
    session.commit()
    
    invitees = review_session['review_session_invitees']

To remove a collaborator simply delete the object using
:meth:`Session.delete`.

.. code-block:: python

    session.delete(invitee)

To send out an invite email to a signle collaborator use
:meth:`Session.send_review_session_invite`.

.. code-block:: python

    session.send_review_session_invite(invitee)

Multiple invitees can have emails sent to them in one batch using
:meth:`Session.send_review_session_invites`.

.. code-block:: python

    session.send_review_session_invites(a_list_of_invitees)
