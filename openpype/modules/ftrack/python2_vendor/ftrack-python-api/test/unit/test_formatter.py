# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import termcolor

import ftrack_api.formatter


def colored(text, *args, **kwargs):
    '''Pass through so there are no escape sequences in output.'''
    return text


def test_format(user, mocker):
    '''Return formatted representation of entity.'''
    mocker.patch.object(termcolor, 'colored', colored)

    result = ftrack_api.formatter.format(user)

    # Cannot test entire string as too variable so check for key text.
    assert result.startswith('User\n')
    assert ' username: jenkins' in result
    assert ' email: ' in result


def test_format_using_custom_formatters(user):
    '''Return formatted representation of entity using custom formatters.'''
    result = ftrack_api.formatter.format(
        user, formatters={
            'header': lambda text: '*{0}*'.format(text),
            'label': lambda text: '-{0}'.format(text)
        }
    )

    # Cannot test entire string as too variable so check for key text.
    assert result.startswith('*User*\n')
    assert ' -username: jenkins' in result
    assert ' -email: ' in result


def test_format_filtering(new_user, mocker):
    '''Return formatted representation using custom filter.'''
    mocker.patch.object(termcolor, 'colored', colored)

    with new_user.session.auto_populating(False):
        result = ftrack_api.formatter.format(
            new_user,
            attribute_filter=ftrack_api.formatter.FILTER['ignore_unset']
        )

    # Cannot test entire string as too variable so check for key text.
    assert result.startswith('User\n')
    assert ' username: {0}'.format(new_user['username']) in result
    assert ' email: ' not in result


def test_format_recursive(user, mocker):
    '''Return formatted recursive representation.'''
    mocker.patch.object(termcolor, 'colored', colored)

    user.session.populate(user, 'timelogs.user')

    with user.session.auto_populating(False):
        result = ftrack_api.formatter.format(user, recursive=True)

    # Cannot test entire string as too variable so check for key text.
    assert result.startswith('User\n')
    assert ' username: jenkins'
    assert ' timelogs: Timelog' in result
    assert ' user: User{...}' in result
