..
    :copyright: Copyright (c) 2017 ftrack

.. _example/invite_user:

*********************
Invite user
*********************

Here we create a new user and send them a invitation through mail


Create a new user::

    user_email = 'artist@mail.vfx-company.com'

    new_user = session.create(
        'User', {
            'username':user_email,
            'email':user_email,
            'is_active':True
        }
    )

    session.commit()


Invite our new user::

    new_user.send_invite()

