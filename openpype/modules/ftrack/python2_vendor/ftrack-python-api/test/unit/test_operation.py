# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import ftrack_api.operation


def test_operations_initialise():
    '''Initialise empty operations stack.'''
    operations = ftrack_api.operation.Operations()
    assert len(operations) == 0


def test_operations_push():
    '''Push new operation onto stack.'''
    operations = ftrack_api.operation.Operations()
    assert len(operations) == 0

    operation = ftrack_api.operation.Operation()
    operations.push(operation)
    assert list(operations)[-1] is operation


def test_operations_pop():
    '''Pop and return operation from stack.'''
    operations = ftrack_api.operation.Operations()
    assert len(operations) == 0

    operations.push(ftrack_api.operation.Operation())
    operations.push(ftrack_api.operation.Operation())
    operation = ftrack_api.operation.Operation()
    operations.push(operation)

    assert len(operations) == 3
    popped = operations.pop()
    assert popped is operation
    assert len(operations) == 2


def test_operations_count():
    '''Count operations in stack.'''
    operations = ftrack_api.operation.Operations()
    assert len(operations) == 0

    operations.push(ftrack_api.operation.Operation())
    assert len(operations) == 1

    operations.pop()
    assert len(operations) == 0


def test_operations_clear():
    '''Clear operations stack.'''
    operations = ftrack_api.operation.Operations()
    operations.push(ftrack_api.operation.Operation())
    operations.push(ftrack_api.operation.Operation())
    operations.push(ftrack_api.operation.Operation())
    assert len(operations) == 3

    operations.clear()
    assert len(operations) == 0


def test_operations_iter():
    '''Iterate over operations stack.'''
    operations = ftrack_api.operation.Operations()
    operation_a = ftrack_api.operation.Operation()
    operation_b = ftrack_api.operation.Operation()
    operation_c = ftrack_api.operation.Operation()

    operations.push(operation_a)
    operations.push(operation_b)
    operations.push(operation_c)

    assert len(operations) == 3
    for operation, expected in zip(
        operations, [operation_a, operation_b, operation_c]
    ):
        assert operation is expected

