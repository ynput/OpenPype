# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import os
import textwrap
import logging
import re

import pytest

import ftrack_api.plugin


@pytest.fixture()
def valid_plugin(temporary_path):
    '''Return path to directory containing a valid plugin.'''
    with open(os.path.join(temporary_path, 'plugin.py'), 'w') as file_object:
        file_object.write(textwrap.dedent('''
            def register(*args, **kw):
                print "Registered", args, kw
        '''))

    return temporary_path


@pytest.fixture()
def python_non_plugin(temporary_path):
    '''Return path to directory containing Python file that is non plugin.'''
    with open(os.path.join(temporary_path, 'non.py'), 'w') as file_object:
        file_object.write(textwrap.dedent('''
            print "Not a plugin"

            def not_called():
                print "Not called"
        '''))

    return temporary_path


@pytest.fixture()
def non_plugin(temporary_path):
    '''Return path to directory containing file that is non plugin.'''
    with open(os.path.join(temporary_path, 'non.txt'), 'w') as file_object:
        file_object.write('Never seen')

    return temporary_path


@pytest.fixture()
def broken_plugin(temporary_path):
    '''Return path to directory containing broken plugin.'''
    with open(os.path.join(temporary_path, 'broken.py'), 'w') as file_object:
        file_object.write('syntax error')

    return temporary_path


@pytest.fixture()
def plugin(request, temporary_path):
    '''Return path containing a plugin with requested specification.'''
    specification = request.param
    output = re.sub('(\w+)=\w+', '"\g<1>={}".format(\g<1>)', specification)
    output = re.sub('\*args', 'args', output)
    output = re.sub('\*\*kwargs', 'sorted(kwargs.items())', output)

    with open(os.path.join(temporary_path, 'plugin.py'), 'w') as file_object:
        content = textwrap.dedent('''
            def register({}):
                print {}
        '''.format(specification, output))
        file_object.write(content)

    return temporary_path


def test_discover_empty_paths(capsys):
    '''Discover no plugins when paths are empty.'''
    ftrack_api.plugin.discover(['   '])
    output, error = capsys.readouterr()
    assert not output
    assert not error


def test_discover_valid_plugin(valid_plugin, capsys):
    '''Discover valid plugin.'''
    ftrack_api.plugin.discover([valid_plugin], (1, 2), {'3': 4})
    output, error = capsys.readouterr()
    assert 'Registered (1, 2) {\'3\': 4}' in output


def test_discover_python_non_plugin(python_non_plugin, capsys):
    '''Discover Python non plugin.'''
    ftrack_api.plugin.discover([python_non_plugin])
    output, error = capsys.readouterr()
    assert 'Not a plugin' in output
    assert 'Not called' not in output


def test_discover_non_plugin(non_plugin, capsys):
    '''Discover non plugin.'''
    ftrack_api.plugin.discover([non_plugin])
    output, error = capsys.readouterr()
    assert not output
    assert not error


def test_discover_broken_plugin(broken_plugin, caplog):
    '''Discover broken plugin.'''
    ftrack_api.plugin.discover([broken_plugin])

    records = caplog.records()
    assert len(records) == 1
    assert records[0].levelno is logging.WARNING
    assert 'Failed to load plugin' in records[0].message


@pytest.mark.parametrize(
    'plugin, positional, keyword, expected',
    [
        (
            'a, b=False, c=False, d=False',
            (1, 2), {'c': True, 'd': True, 'e': True},
            '1 b=2 c=True d=True'
        ),
        (
            '*args',
            (1, 2), {'b': True, 'c': False},
            '(1, 2)'
        ),
        (
            '**kwargs',
            tuple(), {'b': True, 'c': False},
            '[(\'b\', True), (\'c\', False)]'
        ),
        (
            'a=False, b=False',
            (True,), {'b': True},
            'a=True b=True'
        ),
        (
            'a, c=False, *args',
            (1, 2, 3, 4), {},
            '1 c=2 (3, 4)'
        ),
        (
            'a, c=False, **kwargs',
            tuple(), {'a': 1, 'b': 2, 'c': 3, 'd': 4},
            '1 c=3 [(\'b\', 2), (\'d\', 4)]'
        ),
    ],
    indirect=['plugin'],
    ids=[
        'mixed-explicit',
        'variable-args-only',
        'variable-kwargs-only',
        'keyword-from-positional',
        'trailing-variable-args',
        'trailing-keyword-args'
    ]
)
def test_discover_plugin_with_specific_signature(
    plugin, positional, keyword, expected, capsys
):
    '''Discover plugin passing only supported arguments.'''
    ftrack_api.plugin.discover(
        [plugin], positional, keyword
    )
    output, error = capsys.readouterr()
    assert expected in output


def test_discover_plugin_varying_signatures(temporary_path, capsys):
    '''Discover multiple plugins with varying signatures.'''
    with open(os.path.join(temporary_path, 'plugin_a.py'), 'w') as file_object:
        file_object.write(textwrap.dedent('''
            def register(a):
                print (a,)
        '''))

    with open(os.path.join(temporary_path, 'plugin_b.py'), 'w') as file_object:
        file_object.write(textwrap.dedent('''
            def register(a, b=False):
                print (a,), {'b': b}
        '''))

    ftrack_api.plugin.discover(
        [temporary_path], (True,), {'b': True}
    )

    output, error = capsys.readouterr()
    assert '(True,)'in output
    assert '(True,) {\'b\': True}' in output
