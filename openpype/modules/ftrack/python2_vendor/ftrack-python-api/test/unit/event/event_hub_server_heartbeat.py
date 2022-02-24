# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

import sys
import time
import logging
import argparse

import ftrack_api
from ftrack_api.event.base import Event


TOPIC = 'test_event_hub_server_heartbeat'
RECEIVED = []


def callback(event):
    '''Track received messages.'''
    counter = event['data']['counter']
    RECEIVED.append(counter)
    print('Received message {0} ({1} in total)'.format(counter, len(RECEIVED)))


def main(arguments=None):
    '''Publish and receive heartbeat test.'''
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['publish', 'subscribe'])

    namespace = parser.parse_args(arguments)
    logging.basicConfig(level=logging.INFO)

    session = ftrack_api.Session()

    message_count = 100
    sleep_time_per_message = 1

    if namespace.mode == 'publish':
        max_atempts = 100
        retry_interval = 0.1
        atempt = 0
        while not session.event_hub.connected:
            print (
                'Session is not yet connected to event hub, sleeping for 0.1s'
            )
            time.sleep(retry_interval)

            atempt = atempt + 1
            if atempt > max_atempts:
                raise Exception(
                    'Unable to connect to server within {0} seconds'.format(
                        max_atempts * retry_interval
                    )
                )

        print('Sending {0} messages...'.format(message_count))

        for counter in range(1, message_count + 1):
            session.event_hub.publish(
                Event(topic=TOPIC, data=dict(counter=counter))
            )
            print('Sent message {0}'.format(counter))

            if counter < message_count:
                time.sleep(sleep_time_per_message)

    elif namespace.mode == 'subscribe':
        session.event_hub.subscribe('topic={0}'.format(TOPIC), callback)
        session.event_hub.wait(
            duration=(
                ((message_count - 1) * sleep_time_per_message) + 15
            )
        )

        if len(RECEIVED) != message_count:
            print(
                '>> Failed to receive all messages. Dropped {0} <<'
                .format(message_count - len(RECEIVED))
            )
            return False

    # Give time to flush all buffers.
    time.sleep(5)

    return True


if __name__ == '__main__':
    result = main(sys.argv[1:])
    if not result:
        raise SystemExit(1)
    else:
        raise SystemExit(0)
