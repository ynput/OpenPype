# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

from builtins import map
from six import string_types
from builtins import object
from operator import eq, ne, ge, le, gt, lt

from pyparsing import (Group, Word, CaselessKeyword, Forward,
                       FollowedBy, Suppress, oneOf, OneOrMore, Optional,
                       alphanums, quotedString, removeQuotes)

import ftrack_api.exception

# Do not enable packrat since it is not thread-safe and will result in parsing
# exceptions in a multi threaded environment.
# ParserElement.enablePackrat()


class Parser(object):
    '''Parse string based expression into :class:`Expression` instance.'''

    def __init__(self):
        '''Initialise parser.'''
        self._operators = {
            '=': eq,
            '!=': ne,
            '>=': ge,
            '<=': le,
            '>': gt,
            '<': lt
        }
        self._parser = self._construct_parser()
        super(Parser, self).__init__()

    def _construct_parser(self):
        '''Construct and return parser.'''
        field = Word(alphanums + '_.')
        operator = oneOf(list(self._operators.keys()))
        value = Word(alphanums + '-_,./*@+')
        quoted_value = quotedString('quoted_value').setParseAction(removeQuotes)

        condition = Group(
            field + operator + (quoted_value | value)
        )('condition')

        not_ = Optional(Suppress(CaselessKeyword('not')))('not')
        and_ = Suppress(CaselessKeyword('and'))('and')
        or_ = Suppress(CaselessKeyword('or'))('or')

        expression = Forward()
        parenthesis = Suppress('(') + expression + Suppress(')')
        previous = condition | parenthesis

        for conjunction in (not_, and_, or_):
            current = Forward()

            if conjunction in (and_, or_):
                conjunction_expression = (
                    FollowedBy(previous + conjunction + previous)
                    + Group(
                        previous + OneOrMore(conjunction + previous)
                    )(conjunction.resultsName)
                )

            elif conjunction in (not_, ):
                conjunction_expression = (
                    FollowedBy(conjunction.expr + current)
                    + Group(conjunction + current)(conjunction.resultsName)
                )

            else:  # pragma: no cover
                raise ValueError('Unrecognised conjunction.')

            current <<= (conjunction_expression | previous)
            previous = current

        expression <<= previous
        return expression('expression')

    def parse(self, expression):
        '''Parse string *expression* into :class:`Expression`.

        Raise :exc:`ftrack_api.exception.ParseError` if *expression* could
        not be parsed.

        '''
        result = None
        expression = expression.strip()
        if expression:
            try:
                result = self._parser.parseString(
                    expression, parseAll=True
                )
            except Exception as error:
                raise ftrack_api.exception.ParseError(
                    'Failed to parse: {0}. {1}'.format(expression, error)
                )

        return self._process(result)

    def _process(self, result):
        '''Process *result* using appropriate method.

        Method called is determined by the name of the result.

        '''
        method_name = '_process_{0}'.format(result.getName())
        method = getattr(self, method_name)
        return method(result)

    def _process_expression(self, result):
        '''Process *result* as expression.'''
        return self._process(result[0])

    def _process_not(self, result):
        '''Process *result* as NOT operation.'''
        return Not(self._process(result[0]))

    def _process_and(self, result):
        '''Process *result* as AND operation.'''
        return All([self._process(entry) for entry in result])

    def _process_or(self, result):
        '''Process *result* as OR operation.'''
        return Any([self._process(entry) for entry in result])

    def _process_condition(self, result):
        '''Process *result* as condition.'''
        key, operator, value = result
        return Condition(key, self._operators[operator], value)

    def _process_quoted_value(self, result):
        '''Process *result* as quoted value.'''
        return result


class Expression(object):
    '''Represent a structured expression to test candidates against.'''

    def __str__(self):
        '''Return string representation.'''
        return '<{0}>'.format(self.__class__.__name__)

    def match(self, candidate):
        '''Return whether *candidate* satisfies this expression.'''
        return True


class All(Expression):
    '''Match candidate that matches all of the specified expressions.

    .. note::

        If no expressions are supplied then will always match.

    '''

    def __init__(self, expressions=None):
        '''Initialise with list of *expressions* to match against.'''
        self._expressions = expressions or []
        super(All, self).__init__()

    def __str__(self):
        '''Return string representation.'''
        return '<{0} [{1}]>'.format(
            self.__class__.__name__,
            ' '.join(map(str, self._expressions))
        )

    def match(self, candidate):
        '''Return whether *candidate* satisfies this expression.'''
        return all([
            expression.match(candidate) for expression in self._expressions
        ])


class Any(Expression):
    '''Match candidate that matches any of the specified expressions.

    .. note::

        If no expressions are supplied then will never match.

    '''

    def __init__(self, expressions=None):
        '''Initialise with list of *expressions* to match against.'''
        self._expressions = expressions or []
        super(Any, self).__init__()

    def __str__(self):
        '''Return string representation.'''
        return '<{0} [{1}]>'.format(
            self.__class__.__name__,
            ' '.join(map(str, self._expressions))
        )

    def match(self, candidate):
        '''Return whether *candidate* satisfies this expression.'''
        return any([
            expression.match(candidate) for expression in self._expressions
        ])


class Not(Expression):
    '''Negate expression.'''

    def __init__(self, expression):
        '''Initialise with *expression* to negate.'''
        self._expression = expression
        super(Not, self).__init__()

    def __str__(self):
        '''Return string representation.'''
        return '<{0} {1}>'.format(
            self.__class__.__name__,
            self._expression
        )

    def match(self, candidate):
        '''Return whether *candidate* satisfies this expression.'''
        return not self._expression.match(candidate)


class Condition(Expression):
    '''Represent condition.'''

    def __init__(self, key, operator, value):
        '''Initialise condition.

        *key* is the key to check on the data when matching. It can be a nested
        key represented by dots. For example, 'data.eventType' would attempt to
        match candidate['data']['eventType']. If the candidate is missing any
        of the requested keys then the match fails immediately.

        *operator* is the operator function to use to perform the match between
        the retrieved candidate value and the conditional *value*.

        If *value* is a string, it can use a wildcard '*' at the end to denote
        that any values matching the substring portion are valid when matching
        equality only.

        '''
        self._key = key
        self._operator = operator
        self._value = value
        self._wildcard = '*'
        self._operatorMapping = {
            eq: '=',
            ne: '!=',
            ge: '>=',
            le: '<=',
            gt: '>',
            lt: '<'
        }

    def __str__(self):
        '''Return string representation.'''
        return '<{0} {1}{2}{3}>'.format(
            self.__class__.__name__,
            self._key,
            self._operatorMapping.get(self._operator, self._operator),
            self._value
        )

    def match(self, candidate):
        '''Return whether *candidate* satisfies this expression.'''
        key_parts = self._key.split('.')

        try:
            value = candidate
            for keyPart in key_parts:
                value = value[keyPart]
        except (KeyError, TypeError):
            return False

        if (
            self._operator is eq
            and isinstance(self._value, string_types)
            and self._value[-1] == self._wildcard
        ):
            return self._value[:-1] in value
        else:
            return self._operator(value, self._value)
