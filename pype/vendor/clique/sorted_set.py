# :coding: utf-8
# :copyright: Copyright (c) 2013 Martin Pengelly-Phillips
# :license: See LICENSE.txt.

import collections
import bisect


class SortedSet(collections.MutableSet):
    '''Maintain sorted collection of unique items.'''

    def __init__(self, iterable=None):
        '''Initialise with items from *iterable*.'''
        super(SortedSet, self).__init__()
        self._members = []
        if iterable:
            self.update(iterable)

    def __str__(self):
        '''Return string representation.'''
        return str(self._members)

    def __repr__(self):
        '''Return representation.'''
        return '<{0} "{1}">'.format(self.__class__.__name__, self)

    def __contains__(self, item):
        '''Return whether *item* is present.'''
        return self._index(item) >= 0

    def __len__(self):
        '''Return number of items.'''
        return len(self._members)

    def __iter__(self):
        '''Return iterator over items.'''
        return iter(self._members)

    def add(self, item):
        '''Add *item*.'''
        if not item in self:
            index = bisect.bisect_right(self._members, item)
            self._members.insert(index, item)

    def discard(self, item):
        '''Remove *item*.'''
        index = self._index(item)
        if index >= 0:
            del self._members[index]

    def update(self, iterable):
        '''Update items with those from *iterable*.'''
        for item in iterable:
            self.add(item)

    def _index(self, item):
        '''Return index of *item* in member list or -1 if not present.'''
        index = bisect.bisect_left(self._members, item)
        if index != len(self) and self._members[index] == item:
            return index

        return -1
