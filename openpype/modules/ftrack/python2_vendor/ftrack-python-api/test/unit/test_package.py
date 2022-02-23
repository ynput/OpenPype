# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import ftrack_api


class Class(object):
    '''Class.'''


class Mixin(object):
    '''Mixin.'''

    def method(self):
        '''Method.'''
        return True


def test_mixin():
    '''Mixin class to instance.'''
    instance_a = Class()
    instance_b = Class()

    assert not hasattr(instance_a, 'method')
    assert not hasattr(instance_b, 'method')

    ftrack_api.mixin(instance_a, Mixin)

    assert hasattr(instance_a, 'method')
    assert instance_a.method() is True
    assert not hasattr(instance_b, 'method')


def test_mixin_same_class_multiple_times():
    '''Mixin class to instance multiple times.'''
    instance = Class()
    assert not hasattr(instance, 'method')
    assert len(instance.__class__.mro()) == 2

    ftrack_api.mixin(instance, Mixin)
    assert hasattr(instance, 'method')
    assert instance.method() is True
    assert len(instance.__class__.mro()) == 4

    ftrack_api.mixin(instance, Mixin)
    assert hasattr(instance, 'method')
    assert instance.method() is True
    assert len(instance.__class__.mro()) == 4
