..
    :copyright: Copyright (c) 2015 ftrack

.. _example/timer:

************
Using timers
************

.. currentmodule:: ftrack_api.session

Timers can be used to track how much time has been spend working on something.

To start a timer for a user::

    user = # Get a user from ftrack.
    task = # Get a task from ftrack.

    user.start_timer(task)

A timer has now been created for that user and should show up in the ftrack web
UI.

To stop the currently running timer for a user and create a timelog from it::

    user = # Get a user from ftrack.

    timelog = user.stop_timer()

.. note::

    Starting a timer when a timer is already running will raise in an exception.
    Use the force parameter to automatically stop the running timer first.

    .. code-block:: python

        user.start_timer(task, force=True)
