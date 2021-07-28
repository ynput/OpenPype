# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import inspect
import json
import os
import time
import subprocess
import sys

import pytest

import ftrack_api.event.hub
import ftrack_api.event.subscriber
from ftrack_api.event.base import Event
import ftrack_api.exception


class MockClass(object):
    '''Mock class for testing.'''

    def method(self):
        '''Mock method for testing.'''


def mockFunction():
    '''Mock function for testing.'''


class MockConnection(object):
    '''Mock connection for testing.'''

    @property
    def connected(self):
        '''Return whether connected.'''
        return True

    def close(self):
        '''Close mock connection.'''
        pass


def assert_callbacks(hub, callbacks):
    '''Assert hub has exactly *callbacks* subscribed.'''
    # Subscribers always starts with internal handle_reply subscriber.
    subscribers = hub._subscribers[:]
    subscribers.pop(0)

    if len(subscribers) != len(callbacks):
        raise AssertionError(
            'Number of subscribers ({0}) != number of callbacks ({1})'
            .format(len(subscribers), len(callbacks))
        )

    for index, subscriber in enumerate(subscribers):
        if subscriber.callback != callbacks[index]:
            raise AssertionError(
                'Callback at {0} != subscriber callback at same index.'
                .format(index)
            )


@pytest.fixture()
def event_hub(request, session):
    '''Return event hub to test against.

    Hub is automatically connected at start of test and disconnected at end.

    '''
    hub = ftrack_api.event.hub.EventHub(
        session.server_url, session.api_user, session.api_key
    )
    hub.connect()

    def cleanup():
        '''Cleanup.'''
        if hub.connected:
            hub.disconnect()

    request.addfinalizer(cleanup)

    return hub


@pytest.mark.parametrize('server_url, expected', [
    ('https://test.ftrackapp.com', 'https://test.ftrackapp.com'),
    ('https://test.ftrackapp.com:9000', 'https://test.ftrackapp.com:9000')
], ids=[
    'with port',
    'without port'
])
def test_get_server_url(server_url, expected):
    '''Return server url.'''
    event_hub = ftrack_api.event.hub.EventHub(
        server_url, 'user', 'key'
    )
    assert event_hub.get_server_url() == expected


@pytest.mark.parametrize('server_url, expected', [
    ('https://test.ftrackapp.com', 'test.ftrackapp.com'),
    ('https://test.ftrackapp.com:9000', 'test.ftrackapp.com:9000')
], ids=[
    'with port',
    'without port'
])
def test_get_network_location(server_url, expected):
    '''Return network location of server url.'''
    event_hub = ftrack_api.event.hub.EventHub(
        server_url, 'user', 'key'
    )
    assert event_hub.get_network_location() == expected


@pytest.mark.parametrize('server_url, expected', [
    ('https://test.ftrackapp.com', True),
    ('http://test.ftrackapp.com', False)
], ids=[
    'secure',
    'not secure'
])
def test_secure_property(server_url, expected, mocker):
    '''Return whether secure connection used.'''
    event_hub = ftrack_api.event.hub.EventHub(
        server_url, 'user', 'key'
    )
    assert event_hub.secure is expected


def test_connected_property(session):
    '''Return connected state.'''
    event_hub = ftrack_api.event.hub.EventHub(
        session.server_url, session.api_user, session.api_key
    )
    assert event_hub.connected is False

    event_hub.connect()
    assert event_hub.connected is True

    event_hub.disconnect()
    assert event_hub.connected is False


@pytest.mark.parametrize('server_url, expected', [
    ('https://test.ftrackapp.com', 'https://test.ftrackapp.com'),
    ('https://test.ftrackapp.com:9000', 'https://test.ftrackapp.com:9000'),
    ('test.ftrackapp.com', ValueError),
    ('https://:9000', ValueError),
], ids=[
    'with port',
    'without port',
    'missing scheme',
    'missing hostname'
])
def test_initialise_against_server_url(server_url, expected):
    '''Initialise against server url.'''
    if inspect.isclass(expected) and issubclass(expected, Exception):
        with pytest.raises(expected):
            ftrack_api.event.hub.EventHub(
                server_url, 'user', 'key'
            )
    else:
        event_hub = ftrack_api.event.hub.EventHub(
            server_url, 'user', 'key'
        )
        assert event_hub.get_server_url() == expected


def test_connect(session):
    '''Connect.'''
    event_hub = ftrack_api.event.hub.EventHub(
        session.server_url, session.api_user, session.api_key
    )
    event_hub.connect()

    assert event_hub.connected is True
    event_hub.disconnect()


def test_connect_when_already_connected(event_hub):
    '''Fail to connect when already connected'''
    assert event_hub.connected is True

    with pytest.raises(ftrack_api.exception.EventHubConnectionError) as error:
        event_hub.connect()

    assert 'Already connected' in str(error)


def test_connect_failure(session, mocker):
    '''Fail to connect to server.'''
    event_hub = ftrack_api.event.hub.EventHub(
        session.server_url, session.api_user, session.api_key
    )

    def force_fail(*args, **kwargs):
        '''Force connection failure.'''
        raise Exception('Forced fail.')

    mocker.patch('websocket.create_connection', force_fail)
    with pytest.raises(ftrack_api.exception.EventHubConnectionError):
        event_hub.connect()


def test_connect_missing_required_transport(session, mocker, caplog):
    '''Fail to connect to server that does not provide correct transport.'''
    event_hub = ftrack_api.event.hub.EventHub(
        session.server_url, session.api_user, session.api_key
    )

    original_get_socket_io_session = event_hub._get_socket_io_session

    def _get_socket_io_session():
        '''Patched to return no transports.'''
        session = original_get_socket_io_session()
        return ftrack_api.event.hub.SocketIoSession(
            session[0], session[1], []
        )

    mocker.patch.object(
        event_hub, '_get_socket_io_session', _get_socket_io_session
    )

    with pytest.raises(ftrack_api.exception.EventHubConnectionError):
        event_hub.connect()

    logs = caplog.records()
    assert (
        'Server does not support websocket sessions.' in str(logs[-1].exc_info)
    )


def test_disconnect(event_hub):
    '''Disconnect and unsubscribe all subscribers.'''
    event_hub.disconnect()
    assert len(event_hub._subscribers) == 0
    assert event_hub.connected is False


def test_disconnect_without_unsubscribing(event_hub):
    '''Disconnect without unsubscribing all subscribers.'''
    event_hub.disconnect(unsubscribe=False)
    assert len(event_hub._subscribers) > 0
    assert event_hub.connected is False


def test_close_connection_from_manually_connected_hub(session_no_autoconnect_hub):
    '''Close connection from manually connected hub.'''
    session_no_autoconnect_hub.event_hub.connect()
    session_no_autoconnect_hub.close()
    assert session_no_autoconnect_hub.event_hub.connected is False


def test_disconnect_when_not_connected(session):
    '''Fail to disconnect when not connected'''
    event_hub = ftrack_api.event.hub.EventHub(
        session.server_url, session.api_user, session.api_key
    )
    with pytest.raises(ftrack_api.exception.EventHubConnectionError) as error:
        event_hub.disconnect()

    assert 'Not currently connected' in str(error)


def test_reconnect(event_hub):
    '''Reconnect successfully.'''
    assert event_hub.connected is True
    event_hub.reconnect()
    assert event_hub.connected is True


def test_reconnect_when_not_connected(session):
    '''Reconnect successfully even if not already connected.'''
    event_hub = ftrack_api.event.hub.EventHub(
        session.server_url, session.api_user, session.api_key
    )
    assert event_hub.connected is False

    event_hub.reconnect()
    assert event_hub.connected is True

    event_hub.disconnect()


def test_fail_to_reconnect(session, mocker):
    '''Fail to reconnect.'''
    event_hub = ftrack_api.event.hub.EventHub(
        session.server_url, session.api_user, session.api_key
    )
    event_hub.connect()
    assert event_hub.connected is True

    def force_fail(*args, **kwargs):
        '''Force connection failure.'''
        raise Exception('Forced fail.')

    mocker.patch('websocket.create_connection', force_fail)

    attempts = 2
    with pytest.raises(ftrack_api.exception.EventHubConnectionError) as error:
        event_hub.reconnect(attempts=attempts, delay=0.5)

    assert 'Failed to reconnect to event server' in str(error)
    assert 'after {} attempts'.format(attempts) in str(error)


def test_wait(event_hub):
    '''Wait for event and handle as they arrive.'''
    called = {'callback': False}

    def callback(event):
        called['callback'] = True

    event_hub.subscribe('topic=test-subscribe', callback)

    event_hub.publish(Event(topic='test-subscribe'))

    # Until wait, the event should not have been processed even if received.
    time.sleep(1)
    assert called == {'callback': False}

    event_hub.wait(2)
    assert called == {'callback': True}


def test_wait_interrupted_by_disconnect(event_hub):
    '''Interrupt wait loop with disconnect event.'''
    wait_time = 5
    start = time.time()

    # Inject event directly for test purposes.
    event = Event(topic='ftrack.meta.disconnected')
    event_hub._event_queue.put(event)

    event_hub.wait(wait_time)

    assert time.time() - start < wait_time


@pytest.mark.parametrize('identifier, registered', [
    ('registered-test-subscriber', True),
    ('unregistered-test-subscriber', False)
], ids=[
    'registered',
    'missing'
])
def test_get_subscriber_by_identifier(event_hub, identifier, registered):
    '''Return subscriber by identifier.'''
    def callback(event):
        pass

    subscriber = {
        'id': 'registered-test-subscriber'
    }

    event_hub.subscribe('topic=test-subscribe', callback, subscriber)
    retrieved = event_hub.get_subscriber_by_identifier(identifier)

    if registered:
        assert isinstance(retrieved, ftrack_api.event.subscriber.Subscriber)
        assert retrieved.metadata.get('id') == subscriber['id']
    else:
        assert retrieved is None


def test_subscribe(event_hub):
    '''Subscribe to topics.'''
    called = {'a': False, 'b': False}

    def callback_a(event):
        called['a'] = True

    def callback_b(event):
        called['b'] = True

    event_hub.subscribe('topic=test-subscribe', callback_a)
    event_hub.subscribe('topic=test-subscribe-other', callback_b)

    event_hub.publish(Event(topic='test-subscribe'))
    event_hub.wait(2)

    assert called == {'a': True, 'b': False}


def test_subscribe_before_connected(session):
    '''Subscribe to topic before connected.'''
    event_hub = ftrack_api.event.hub.EventHub(
        session.server_url, session.api_user, session.api_key
    )

    called = {'callback': False}

    def callback(event):
        called['callback'] = True

    identifier = 'test-subscriber'
    event_hub.subscribe(
        'topic=test-subscribe', callback, subscriber={'id': identifier}
    )
    assert event_hub.get_subscriber_by_identifier(identifier) is not None

    event_hub.connect()

    try:
        event_hub.publish(Event(topic='test-subscribe'))
        event_hub.wait(2)
    finally:
        event_hub.disconnect()

    assert called == {'callback': True}


def test_duplicate_subscriber(event_hub):
    '''Fail to subscribe same subscriber more than once.'''
    subscriber = {'id': 'test-subscriber'}
    event_hub.subscribe('topic=test', None, subscriber=subscriber)

    with pytest.raises(ftrack_api.exception.NotUniqueError) as error:
        event_hub.subscribe('topic=test', None, subscriber=subscriber)

    assert '{0} already exists'.format(subscriber['id']) in str(error)


def test_unsubscribe(event_hub):
    '''Unsubscribe a specific callback.'''
    def callback_a(event):
        pass

    def callback_b(event):
        pass

    identifier_a = event_hub.subscribe('topic=test', callback_a)
    identifier_b = event_hub.subscribe('topic=test', callback_b)

    assert_callbacks(event_hub, [callback_a, callback_b])

    event_hub.unsubscribe(identifier_a)

    # Unsubscribe requires confirmation event so wait here to give event a
    # chance to process.
    time.sleep(5)

    assert_callbacks(event_hub, [callback_b])


def test_unsubscribe_whilst_disconnected(event_hub):
    '''Unsubscribe whilst disconnected.'''
    identifier = event_hub.subscribe('topic=test', None)
    event_hub.disconnect(unsubscribe=False)

    event_hub.unsubscribe(identifier)
    assert_callbacks(event_hub, [])


def test_unsubscribe_missing_subscriber(event_hub):
    '''Fail to unsubscribe a non-subscribed subscriber.'''
    identifier = 'non-subscribed-subscriber'
    with pytest.raises(ftrack_api.exception.NotFoundError) as error:
        event_hub.unsubscribe(identifier)

    assert (
        'missing subscriber with identifier {}'.format(identifier)
        in str(error)
    )


@pytest.mark.parametrize('event_data', [
    dict(source=dict(id='1', user=dict(username='auto'))),
    dict(source=dict(user=dict(username='auto'))),
    dict(source=dict(id='1')),
    dict()
], ids=[
    'pre-prepared',
    'missing id',
    'missing user',
    'no source'
])
def test_prepare_event(session, event_data):
    '''Prepare event.'''
    # Replace username `auto` in event data with API user.
    try:
        if event_data['source']['user']['username'] == 'auto':
            event_data['source']['user']['username'] = session.api_user
    except KeyError:
        pass

    event_hub = ftrack_api.event.hub.EventHub(
        session.server_url, session.api_user, session.api_key
    )
    event_hub.id = '1'

    event = Event('test', id='event-id', **event_data)
    expected = Event(
        'test', id='event-id', source=dict(id='1', user=dict(username=session.api_user))
    )
    event_hub._prepare_event(event)
    assert event == expected


def test_prepare_reply_event(session):
    '''Prepare reply event.'''
    event_hub = ftrack_api.event.hub.EventHub(
        session.server_url, session.api_user, session.api_key
    )

    source_event = Event('source', source=dict(id='source-id'))
    reply_event = Event('reply')

    event_hub._prepare_reply_event(reply_event, source_event)
    assert source_event['source']['id'] in reply_event['target']
    assert reply_event['in_reply_to_event'] == source_event['id']

    event_hub._prepare_reply_event(reply_event, source_event, {'id': 'source'})
    assert reply_event['source'] == {'id': 'source'}


def test_publish(event_hub):
    '''Publish asynchronous event.'''
    called = {'callback': False}

    def callback(event):
        called['callback'] = True

    event_hub.subscribe('topic=test-subscribe', callback)

    event_hub.publish(Event(topic='test-subscribe'))
    event_hub.wait(2)

    assert called == {'callback': True}


def test_publish_raising_error(event_hub):
    '''Raise error, when configured, on failed publish.'''
    # Note that the event hub currently only fails publish when not connected.
    # All other errors are inconsistently swallowed.
    event_hub.disconnect()
    event = Event(topic='a-topic', data=dict(status='fail'))

    with pytest.raises(Exception):
        event_hub.publish(event, on_error='raise')


def test_publish_ignoring_error(event_hub):
    '''Ignore error, when configured, on failed publish.'''
    # Note that the event hub currently only fails publish when not connected.
    # All other errors are inconsistently swallowed.
    event_hub.disconnect()
    event = Event(topic='a-topic', data=dict(status='fail'))
    event_hub.publish(event, on_error='ignore')


def test_publish_logs_other_errors(event_hub, caplog, mocker):
    '''Log publish errors other than connection error.'''
    # Mock connection to force error.
    mocker.patch.object(event_hub, '_connection', MockConnection())

    event = Event(topic='a-topic', data=dict(status='fail'))
    event_hub.publish(event)

    expected = 'Error sending event {0}.'.format(event)
    messages = [record.getMessage().strip() for record in caplog.records()]
    assert expected in messages, 'Expected log message missing in output.'


def test_synchronous_publish(event_hub):
    '''Publish event synchronously and collect results.'''
    def callback_a(event):
        return 'A'

    def callback_b(event):
        return 'B'

    def callback_c(event):
        return 'C'

    event_hub.subscribe('topic=test', callback_a, priority=50)
    event_hub.subscribe('topic=test', callback_b, priority=60)
    event_hub.subscribe('topic=test', callback_c, priority=70)

    results = event_hub.publish(Event(topic='test'), synchronous=True)
    assert results == ['A', 'B', 'C']


def test_publish_with_reply(event_hub):
    '''Publish asynchronous event with on reply handler.'''

    def replier(event):
        '''Replier.'''
        return 'Replied'

    event_hub.subscribe('topic=test', replier)

    called = {'callback': None}

    def on_reply(event):
        called['callback'] = event['data']

    event_hub.publish(Event(topic='test'), on_reply=on_reply)
    event_hub.wait(2)

    assert called['callback'] == 'Replied'


def test_publish_with_multiple_replies(event_hub):
    '''Publish asynchronous event and retrieve multiple replies.'''

    def replier_one(event):
        '''Replier.'''
        return 'One'

    def replier_two(event):
        '''Replier.'''
        return 'Two'

    event_hub.subscribe('topic=test', replier_one)
    event_hub.subscribe('topic=test', replier_two)

    called = {'callback': []}

    def on_reply(event):
        called['callback'].append(event['data'])

    event_hub.publish(Event(topic='test'), on_reply=on_reply)
    event_hub.wait(2)

    assert sorted(called['callback']) == ['One', 'Two']


@pytest.mark.slow
def test_server_heartbeat_response():
    '''Maintain connection by responding to server heartbeat request.'''
    test_script = os.path.join(
        os.path.dirname(__file__), 'event_hub_server_heartbeat.py'
    )

    # Start subscriber that will listen for all three messages.
    subscriber = subprocess.Popen([sys.executable, test_script, 'subscribe'])

    # Give subscriber time to connect to server.
    time.sleep(10)

    # Start publisher to publish three messages.
    publisher = subprocess.Popen([sys.executable, test_script, 'publish'])

    publisher.wait()
    subscriber.wait()

    assert subscriber.returncode == 0


def test_stop_event(event_hub):
    '''Stop processing of subsequent local handlers when stop flag set.'''
    called = {
        'a': False,
        'b': False,
        'c': False
    }

    def callback_a(event):
        called['a'] = True

    def callback_b(event):
        called['b'] = True
        event.stop()

    def callback_c(event):
        called['c'] = True

    event_hub.subscribe('topic=test', callback_a, priority=50)
    event_hub.subscribe('topic=test', callback_b, priority=60)
    event_hub.subscribe('topic=test', callback_c, priority=70)

    event_hub.publish(Event(topic='test'))
    event_hub.wait(2)

    assert called == {
        'a': True,
        'b': True,
        'c': False
    }


def test_encode(session):
    '''Encode event data.'''
    encoded = session.event_hub._encode(
        dict(name='ftrack.event', args=[Event('test')])
    )
    assert 'inReplyToEvent' in encoded
    assert 'in_reply_to_event' not in encoded


def test_decode(session):
    '''Decode event data.'''
    decoded = session.event_hub._decode(
        json.dumps({
            'inReplyToEvent': 'id'
        })
    )

    assert 'in_reply_to_event' in decoded
    assert 'inReplyToEvent' not in decoded
