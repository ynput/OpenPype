# :coding: utf-8
# :copyright: Copyright (c) 2013 Martin Pengelly-Phillips
# :license: See LICENSE.txt.

import re

import clique.descriptor
import clique.error
import clique.sorted_set


class Collection(object):
    '''Represent group of items that differ only by numerical component.'''

    indexes = clique.descriptor.Unsettable('indexes')

    def __init__(self, head, tail, padding, indexes=None):
        '''Initialise collection.

        *head* is the leading common part whilst *tail* is the trailing
        common part.

        *padding* specifies the "width" of the numerical component. An index
        will be padded with zeros to fill this width. A *padding* of zero
        implies no padding and width may be any size so long as no leading
        zeros are present.

        *indexes* can specify a set of numerical indexes to initially populate
        the collection with.

        .. note::

            After instantiation, the ``indexes`` attribute cannot be set to a
            new value using assignment::

                >>> collection.indexes = [1, 2, 3]
                AttributeError: Cannot set attribute defined as unsettable.

            Instead, manipulate it directly::

                >>> collection.indexes.clear()
                >>> collection.indexes.update([1, 2, 3])

        '''
        super(Collection, self).__init__()
        self.__dict__['indexes'] = clique.sorted_set.SortedSet()
        self._head = head
        self._tail = tail
        self.padding = padding
        self._update_expression()

        if indexes is not None:
            self.indexes.update(indexes)

    @property
    def head(self):
        '''Return common leading part.'''
        return self._head

    @head.setter
    def head(self, value):
        '''Set common leading part to *value*.'''
        self._head = value
        self._update_expression()

    @property
    def tail(self):
        '''Return common trailing part.'''
        return self._tail

    @tail.setter
    def tail(self, value):
        '''Set common trailing part to *value*.'''
        self._tail = value
        self._update_expression()

    def _update_expression(self):
        '''Update internal expression.'''
        self._expression = re.compile(
            '^{0}(?P<index>(?P<padding>0*)\d+?){1}$'
            .format(re.escape(self.head), re.escape(self.tail))
        )

    def __str__(self):
        '''Return string represenation.'''
        return self.format()

    def __repr__(self):
        '''Return representation.'''
        return '<{0} "{1}">'.format(self.__class__.__name__, self)

    def __iter__(self):
        '''Return iterator over items in collection.'''
        for index in self.indexes:
            formatted_index = '{0:0{1}d}'.format(index, self.padding)
            item = '{0}{1}{2}'.format(self.head, formatted_index, self.tail)
            yield item

    def __contains__(self, item):
        '''Return whether *item* is present in collection.'''
        match = self.match(item)
        if not match:
            return False

        if not int(match.group('index')) in self.indexes:
            return False

        return True

    def __eq__(self, other):
        '''Return whether *other* collection is equal.'''
        if not isinstance(other, Collection):
            return NotImplemented

        return all([
            other.head == self.head,
            other.tail == self.tail,
            other.padding == self.padding,
            other.indexes == self.indexes
        ])

    def __ne__(self, other):
        '''Return whether *other* collection is not equal.'''
        result = self.__eq__(other)
        if result is NotImplemented:
            return result

        return not result

    def __gt__(self, other):
        '''Return whether *other* collection is greater than.'''
        if not isinstance(other, Collection):
            return NotImplemented

        a = (self.head, self.tail, self.padding, len(self.indexes))
        b = (other.head, other.tail, other.padding, len(other.indexes))

        return a > b

    def __lt__(self, other):
        '''Return whether *other* collection is less than.'''
        result = self.__gt__(other)
        if result is NotImplemented:
            return result

        return not result

    def __ge__(self, other):
        '''Return whether *other* collection is greater than or equal.'''
        result = self.__eq__(other)
        if result is NotImplemented:
            return result

        if result is False:
            result = self.__gt__(other)

        return result

    def __le__(self, other):
        '''Return whether *other* collection is less than or equal.'''
        result = self.__eq__(other)
        if result is NotImplemented:
            return result

        if result is False:
            result = self.__lt__(other)

        return result

    def match(self, item):
        '''Return whether *item* matches this collection expression.

        If a match is successful return data about the match otherwise return
        None.

        '''
        match = self._expression.match(item)
        if not match:
            return None

        index = match.group('index')
        padded = False
        if match.group('padding'):
            padded = True

        if self.padding == 0:
            if padded:
                return None

        elif len(index) != self.padding:
            return None

        return match

    def add(self, item):
        '''Add *item* to collection.

        raise :py:class:`~clique.error.CollectionError` if *item* cannot be
        added to the collection.

        '''
        match = self.match(item)
        if match is None:
            raise clique.error.CollectionError(
                'Item does not match collection expression.'
            )

        self.indexes.add(int(match.group('index')))

    def remove(self, item):
        '''Remove *item* from collection.

        raise :py:class:`~clique.error.CollectionError` if *item* cannot be
        removed from the collection.

        '''
        match = self.match(item)
        if match is None:
            raise clique.error.CollectionError(
                'Item not present in collection.'
            )

        index = int(match.group('index'))
        try:
            self.indexes.remove(index)
        except KeyError:
            raise clique.error.CollectionError(
                'Item not present in collection.'
            )

    def format(self, pattern='{head}{padding}{tail} [{ranges}]'):
        '''Return string representation as specified by *pattern*.

        Pattern can be any format accepted by Python's standard format function
        and will receive the following keyword arguments as context:

            * *head* - Common leading part of the collection.
            * *tail* - Common trailing part of the collection.
            * *padding* - Padding value in ``%0d`` format.
            * *range* - Total range in the form ``start-end``
            * *ranges* - Comma separated ranges of indexes.
            * *holes* - Comma separated ranges of missing indexes.

        '''
        data = {}
        data['head'] = self.head
        data['tail'] = self.tail

        if self.padding:
            data['padding'] = '%0{0}d'.format(self.padding)
        else:
            data['padding'] = '%d'

        if '{holes}' in pattern:
            data['holes'] = self.holes().format('{ranges}')

        if '{range}' in pattern or '{ranges}' in pattern:
            indexes = list(self.indexes)
            indexes_count = len(indexes)

            if indexes_count == 0:
                data['range'] = ''

            elif indexes_count == 1:
                data['range'] = '{0}'.format(indexes[0])

            else:
                data['range'] = '{0}-{1}'.format(
                    indexes[0], indexes[-1]
                )

        if '{ranges}' in pattern:
            separated = self.separate()
            if len(separated) > 1:
                ranges = [collection.format('{range}')
                          for collection in separated]

            else:
                ranges = [data['range']]

            data['ranges'] = ', '.join(ranges)

        return pattern.format(**data)

    def is_contiguous(self):
        '''Return whether entire collection is contiguous.'''
        previous = None
        for index in self.indexes:
            if previous is None:
                previous = index
                continue

            if index != (previous + 1):
                return False

            previous = index

        return True

    def holes(self):
        '''Return holes in collection.

        Return :py:class:`~clique.collection.Collection` of missing indexes.

        '''
        missing = set([])
        previous = None
        for index in self.indexes:
            if previous is None:
                previous = index
                continue

            if index != (previous + 1):
                missing.update(range(previous + 1, index))

            previous = index

        return Collection(self.head, self.tail, self.padding, indexes=missing)

    def is_compatible(self, collection):
        '''Return whether *collection* is compatible with this collection.

        To be compatible *collection* must have the same head, tail and padding
        properties as this collection.

        '''
        return all([
            isinstance(collection, Collection),
            collection.head == self.head,
            collection.tail == self.tail,
            collection.padding == self.padding
        ])

    def merge(self, collection):
        '''Merge *collection* into this collection.

        If the *collection* is compatible with this collection then update
        indexes with all indexes in *collection*.

        raise :py:class:`~clique.error.CollectionError` if *collection* is not
        compatible with this collection.

        '''
        if not self.is_compatible(collection):
            raise clique.error.CollectionError('Collection is not compatible '
                                               'with this collection.')

        self.indexes.update(collection.indexes)

    def separate(self):
        '''Return contiguous parts of collection as separate collections.

        Return as list of :py:class:`~clique.collection.Collection` instances.

        '''
        collections = []
        start = None
        end = None

        for index in self.indexes:
            if start is None:
                start = index
                end = start
                continue

            if index != (end + 1):
                collections.append(
                    Collection(self.head, self.tail, self.padding,
                               indexes=set(range(start, end + 1)))
                )
                start = index

            end = index

        if start is None:
            collections.append(
                Collection(self.head, self.tail, self.padding)
            )
        else:
            collections.append(
                Collection(self.head, self.tail, self.padding,
                           indexes=range(start, end + 1))
            )

        return collections
