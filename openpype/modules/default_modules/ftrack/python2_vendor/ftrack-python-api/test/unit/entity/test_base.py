# :coding: utf-8
# :copyright: Copyright (c) 2016 ftrack

import pytest


def test_hash(project, task, user):
    '''Entities can be hashed.'''
    test_set = set()
    test_set.add(project)
    test_set.add(task)
    test_set.add(user)

    assert test_set == set((project, task, user))
