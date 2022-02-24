# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

import ftrack_api.event.subscription


class Subscriber(object):
    '''Represent event subscriber.'''

    def __init__(self, subscription, callback, metadata, priority):
        '''Initialise subscriber.'''
        self.subscription = ftrack_api.event.subscription.Subscription(
            subscription
        )
        self.callback = callback
        self.metadata = metadata
        self.priority = priority

    def __str__(self):
        '''Return string representation.'''
        return '<{0} metadata={1} subscription="{2}">'.format(
            self.__class__.__name__, self.metadata, self.subscription
        )

    def interested_in(self, event):
        '''Return whether subscriber interested in *event*.'''
        return self.subscription.includes(event)
