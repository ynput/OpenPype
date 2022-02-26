# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import operator
import inspect

import pytest

from ftrack_api.event.expression import (
    Expression, All, Any, Not, Condition, Parser
)
from ftrack_api.exception import ParseError


@pytest.fixture()
def candidate():
    '''Return common candidate to test expressions against.'''
    return {
        'id': 10,
        'name': 'value',
        'change': {
            'name': 'value',
            'new_value': 10
        }
    }


@pytest.mark.parametrize('expression, expected', [
    pytest.mark.xfail(('', Expression())),
    ('invalid', ParseError),
    ('key=value nor other=value', ParseError),
    ('key=value', Condition('key', operator.eq, 'value')),
    ('key="value"', Condition('key', operator.eq, 'value')),
    (
        'a=b and ((c=d or e!=f) and not g.h > 10)',
        All([
            Condition('a', operator.eq, 'b'),
            All([
                Any([
                    Condition('c', operator.eq, 'd'),
                    Condition('e', operator.ne, 'f')
                ]),
                Not(
                    Condition('g.h', operator.gt, 10)
                )
            ])
        ])
    )
], ids=[
    'empty expression',
    'invalid expression',
    'invalid conjunction',
    'basic condition',
    'basic quoted condition',
    'complex condition'
])
def test_parser_parse(expression, expected):
    '''Parse expression into Expression instances.'''
    parser = Parser()

    if inspect.isclass(expected)and issubclass(expected, Exception):
        with pytest.raises(expected):
            parser.parse(expression)
    else:
        assert str(parser.parse(expression)) == str(expected)


@pytest.mark.parametrize('expression, expected', [
    (Expression(), '<Expression>'),
    (All([Expression(), Expression()]), '<All [<Expression> <Expression>]>'),
    (Any([Expression(), Expression()]), '<Any [<Expression> <Expression>]>'),
    (Not(Expression()), '<Not <Expression>>'),
    (Condition('key', '=', 'value'), '<Condition key=value>')
], ids=[
    'Expression',
    'All',
    'Any',
    'Not',
    'Condition'
])
def test_string_representation(expression, expected):
    '''String representation of expression.'''
    assert str(expression) == expected


@pytest.mark.parametrize('expression, expected', [
    # Expression
    (Expression(), True),

    # All
    (All(), True),
    (All([Expression(), Expression()]), True),
    (All([Expression(), Condition('test', operator.eq, 'value')]), False),

    # Any
    (Any(), False),
    (Any([Expression(), Condition('test', operator.eq, 'value')]), True),
    (Any([
        Condition('test', operator.eq, 'value'),
        Condition('other', operator.eq, 'value')
    ]), False),

    # Not
    (Not(Expression()), False),
    (Not(Not(Expression())), True)
], ids=[
    'Expression-always matches',

    'All-no expressions always matches',
    'All-all match',
    'All-not all match',

    'Any-no expressions never matches',
    'Any-some match',
    'Any-none match',

    'Not-invert positive match',
    'Not-double negative is positive match'
])
def test_match(expression, candidate, expected):
    '''Determine if candidate matches expression.'''
    assert expression.match(candidate) is expected


def parametrize_test_condition_match(metafunc):
    '''Parametrize condition_match tests.'''
    identifiers = []
    data = []

    matrix = {
        # Operator, match, no match
        operator.eq: {
            'match': 10, 'no-match': 20,
            'wildcard-match': 'valu*', 'wildcard-no-match': 'values*'
        },
        operator.ne: {'match': 20, 'no-match': 10},
        operator.ge: {'match': 10, 'no-match': 20},
        operator.le: {'match': 10, 'no-match': 0},
        operator.gt: {'match': 0, 'no-match': 10},
        operator.lt: {'match': 20, 'no-match': 10}
    }

    for operator_function, values in matrix.items():
        for value_label, value in values.items():
            if value_label.startswith('wildcard'):
                key_options = {
                    'plain': 'name',
                    'nested': 'change.name'
                }
            else:
                key_options = {
                    'plain': 'id',
                    'nested': 'change.new_value'
                }

            for key_label, key in key_options.items():
                identifiers.append('{} operator {} key {}'.format(
                    operator_function.__name__, key_label, value_label
                ))

                data.append((
                    key, operator_function, value,
                    'no-match' not in value_label
                ))

    metafunc.parametrize(
        'key, operator, value, expected', data, ids=identifiers
    )


def test_condition_match(key, operator, value, candidate, expected):
    '''Determine if candidate matches condition expression.'''
    condition = Condition(key, operator, value)
    assert condition.match(candidate) is expected
