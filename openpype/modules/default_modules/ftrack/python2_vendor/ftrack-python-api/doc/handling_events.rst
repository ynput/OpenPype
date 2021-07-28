..
    :copyright: Copyright (c) 2014 ftrack

.. _handling_events:

***************
Handling events
***************

.. currentmodule:: ftrack_api.event

Events are generated in ftrack when things happen such as a task being updated
or a new version being published. Each :class:`~ftrack_api.session.Session`
automatically connects to the event server and can be used to subscribe to
specific events and perform an action as a result. That action could be updating
another related entity based on a status change or generating folders when a new
shot is created for example.

The :class:`~hub.EventHub` for each :class:`~ftrack_api.session.Session` is
accessible via :attr:`Session.event_hub
<~ftrack_api.session.Session.event_hub>`.

.. _handling_events/subscribing:

Subscribing to events
=====================

To listen to events, you register a function against a subscription using
:meth:`Session.event_hub.subscribe <hub.EventHub.subscribe>`. The subscription
uses the :ref:`expression <handling_events/expressions>` syntax and will filter
against each :class:`~base.Event` instance to determine if the registered
function should receive that event. If the subscription matches, the registered
function will be called with the :class:`~base.Event` instance as its sole
argument. The :class:`~base.Event` instance is a mapping like structure and can
be used like a normal dictionary.

The following example subscribes a function to receive all 'ftrack.update'
events and then print out the entities that were updated::

    import ftrack_api


    def my_callback(event):
        '''Event callback printing all new or updated entities.'''
        for entity in event['data'].get('entities', []):

            # Print data for the entity.
            print(entity)


    # Subscribe to events with the update topic.
    session = ftrack_api.Session()
    session.event_hub.subscribe('topic=ftrack.update', my_callback)

At this point, if you run this, your code would exit almost immediately. This
is because the event hub listens for events in a background thread. Typically,
you only want to stay connected whilst using the session, but in some cases you
will want to block and listen for events solely - a dedicated event processor.
To do this, use the :meth:`EventHub.wait <hub.EventHub.wait>` method::

    # Wait for events to be received and handled.
    session.event_hub.wait()

You cancel waiting for events by using a system interrupt (:kbd:`Ctrl-C`).
Alternatively, you can specify a *duration* to process events for::

    # Only wait and process events for 5 seconds.
    session.event_hub.wait(duration=5)

.. note::

    Events are continually received and queued for processing in the background
    as soon as the connection to the server is established. As a result you may
    see a flurry of activity as soon as you call
    :meth:`~hub.EventHub.wait` for the first time.

.. _handling_events/subscribing/subscriber_information:

Subscriber information
----------------------

When subscribing, you can also specify additional information about your
subscriber. This contextual information can be useful when routing events,
particularly when :ref:`targeting events
<handling_events/publishing/targeting>`. By default, the
:class:`~hub.EventHub` will set some default information, but it can be
useful to enhance this. To do so, simply pass in *subscriber* as a dictionary of
data to the :meth:`~hub.EventHub.subscribe` method::

    session.event_hub.subscribe(
        'topic=ftrack.update',
        my_callback,
        subscriber={
            'id': 'my-unique-subscriber-id',
            'applicationId': 'maya'
        }
    )

.. _handling_events/subscribing/sending_replies:

Sending replies
---------------

When handling an event it is sometimes useful to be able to send information
back to the source of the event. For example,
:ref:`ftrack:developing/events/list/ftrack.location.request-resolve` would
expect a resolved path to be sent back.

You can craft a custom reply event if you want, but an easier way is just to
return the appropriate data from your handler. Any non *None* value will be
automatically sent as a reply::

    def on_event(event):
        # Send following data in automatic reply.
        return {'success': True, 'message': 'Cool!'}

    session.event_hub.subscribe('topic=test-reply', on_event)

.. seealso::

    :ref:`handling_events/publishing/handling_replies`

.. note::

    Some events are published :ref:`synchronously
    <handling_events/publishing/synchronously>`. In this case, any returned data
    is passed back to the publisher directly.

.. _handling_events/subscribing/stopping_events:

Stopping events
---------------

The *event* instance passed to each event handler also provides a method for
stopping the event, :meth:`Event.stop <base.Event.stop>`.

Once an event has been stopped, no further handlers for that specific event
will be called **locally**. Other handlers in other processes may still be
called.

Combining this with setting appropriate priorities when subscribing to a topic
allows handlers to prevent lower priority handlers running when desired.

    >>> import ftrack_api
    >>> import ftrack_api.event.base
    >>>
    >>> def callback_a(event):
    ...     '''Stop the event!'''
    ...     print('Callback A')
    ...     event.stop()
    >>>
    >>> def callback_b(event):
    ...     '''Never run.'''
    ...     print('Callback B')
    >>>
    >>> session = ftrack_api.Session()
    >>> session.event_hub.subscribe(
    ...     'topic=test-stop-event', callback_a, priority=10
    ... )
    >>> session.event_hub.subscribe(
    ...     'topic=test-stop-event', callback_b, priority=20
    ... )
    >>> session.event_hub.publish(
    ...     ftrack_api.event.base.Event(topic='test-stop-event')
    ... )
    >>> session.event_hub.wait(duration=5)
    Callback A called.

.. _handling_events/publishing:

Publishing events
=================

So far we have looked at listening to events coming from ftrack. However, you
are also free to publish your own events (or even publish relevant ftrack
events).

To do this, simply construct an instance of :class:`ftrack_api.event.base.Event`
and pass it to :meth:`EventHub.publish <hub.EventHub.publish>` via the session::

    import ftrack_api.event.base

    event = ftrack_api.event.base.Event(
        topic='my-company.some-topic',
        data={'key': 'value'}
    )
    session.event_hub.publish(event)

The event hub will automatically add some information to your event before it
gets published, including the *source* of the event. By default the event source
is just the event hub, but you can customise this to provide more relevant
information if you want. For example, if you were publishing from within Maya::

    session.event_hub.publish(ftrack_api.event.base.Event(
        topic='my-company.some-topic',
        data={'key': 'value'},
        source={
            'applicationId': 'maya'
        }
    ))

Remember that all supplied information can be used by subscribers to filter
events so the more accurate the information the better.

.. _handling_events/publishing/synchronously:

Publish synchronously
---------------------

It is also possible to call :meth:`~hub.EventHub.publish` synchronously by
passing `synchronous=True`. In synchronous mode, only local handlers will be
called. The result from each called handler is collected and all the results
returned together in a list::

    >>> import ftrack_api
    >>> import ftrack_api.event.base
    >>>
    >>> def callback_a(event):
    ...     return 'A'
    >>>
    >>> def callback_b(event):
    ...     return 'B'
    >>>
    >>> session = ftrack_api.Session()
    >>> session.event_hub.subscribe(
    ...     'topic=test-synchronous', callback_a, priority=10
    ... )
    >>> session.event_hub.subscribe(
    ...     'topic=test-synchronous', callback_b, priority=20
    ... )
    >>> results = session.event_hub.publish(
    ...     ftrack_api.event.base.Event(topic='test-synchronous'),
    ...     synchronous=True
    ... )
    >>> print results
    ['A', 'B']

.. _handling_events/publishing/handling_replies:

Handling replies
----------------

When publishing an event it is also possible to pass a callable that will be
called with any :ref:`reply event <handling_events/subscribing/sending_replies>`
received in response to the published event.

To do so, simply pass in a callable as the *on_reply* parameter::

    def handle_reply(event):
        print 'Got reply', event

    session.event_hub.publish(
        ftrack_api.event.base.Event(topic='test-reply'),
        on_reply=handle_reply
    )

.. _handling_events/publishing/targeting:

Targeting events
----------------

In addition to subscribers filtering events to receive, it is also possible to
give an event a specific target to help route it to the right subscriber.

To do this, set the *target* value on the event to an :ref:`expression
<handling_events/expressions>`. The expression will filter against registered
:ref:`subscriber information
<handling_events/subscribing/subscriber_information>`.

For example, if you have many subscribers listening for a event, but only want
one of those subscribers to get the event, you can target the event to the
subscriber using its registered subscriber id::

    session.event_hub.publish(
        ftrack_api.event.base.Event(
            topic='my-company.topic',
            data={'key': 'value'},
            target='id=my-custom-subscriber-id'
        )
    )

.. _handling_events/expressions:

Expressions
===========

An expression is used to filter against a data structure, returning whether the
structure fulfils the expression requirements. Expressions are currently used
for subscriptions when :ref:`subscribing to events
<handling_events/subscribing>` and for targets when :ref:`publishing targeted
events <handling_events/publishing/targeting>`.

The form of the expression is loosely groupings of 'key=value' with conjunctions
to join them.

For example, a common expression for subscriptions is to filter against an event
topic::

    'topic=ftrack.location.component-added'

However, you can also perform more complex filtering, including accessing
nested parameters::

    'topic=ftrack.location.component-added and data.locationId=london'

.. note::

    If the structure being tested does not have any value for the specified
    key reference then it is treated as *not* matching.

You can also use a single wildcard '*' at the end of any value for matching
multiple values. For example, the following would match all events that have a
topic starting with 'ftrack.'::

    'topic=ftrack.*'
