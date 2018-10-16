# :coding: utf-8
# :copyright: Copyright (c) 2013 Martin Pengelly-Phillips
# :license: See LICENSE.txt.


class Unsettable(object):
    '''Prevent standard setting of property.

    Example::

        >>> class Foo(object):
        ...
        ...     x = Unsettable('x')
        ...
        ...     def __init__(self):
        ...         self.__dict__['x'] = True
        ...
        >>> foo = Foo()
        >>> print foo.x
        True
        >>> foo.x = False
        AttributeError: Cannot set attribute defined as unsettable.

    '''

    def __init__(self, label):
        '''Initialise descriptor with property *label*.

        *label* should match the name of the property being described::

            x = Unsettable('x')

        '''
        self.label = label
        super(Unsettable, self).__init__()

    def __get__(self, instance, owner):
        '''Return value of property for *instance*.'''
        return instance.__dict__.get(self.label)

    def __set__(self, instance, value):
        '''Set *value* for *instance* property.'''
        raise AttributeError('Cannot set attribute defined as unsettable.')

