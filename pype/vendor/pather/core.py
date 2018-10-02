
__all__ = ['parse', 'ls', 'ls_iter', 'format']

import os
import re
import string
import glob

from .error import ParseError

# Regex pattern that matches valid file
# TODO: Implement complete pattern if required
RE_FILENAME = '[-\w.,; \[\]]'


def format(pattern, data, allow_partial=True):
    """Format a pattern with a set of data

    Examples:

        Full formatting
        >>> format("{a}/{b}/{c}", {"a": "foo", "b": "bar", "c": "nugget"})
        'foo/bar/nugget'

        Partial formatting
        >>> format("{asset}/{character}", {"asset": "hero"})
        'hero/{character}'

        Disallow partial formatting
        >>> format("{asset}/{character}", {"asset": "hero"},
        ...        allow_partial=False)
        Traceback (most recent call last):
            ...
        KeyError: 'character'

    Args:
        pattern (str): The pattern to format.
        data (dict): The key, value pairs used for formatting.
        allow_partial (bool): Whether to raise error on partial format.

    Returns:
        str: The formatted result
    """

    assert isinstance(data, dict)

    if not all(isinstance(value, basestring) for value in data.values()):
        raise TypeError("The values in the data "
                        "dictionary must be strings")

    if allow_partial:
        return _partial_format(pattern, data)
    else:
        return pattern.format(**data)


def parse(pattern, path):
    """Parse data from a path based on a pattern

    Example:
        >>> pattern = "root/{task}/{version}/data/"
        >>> path = "root/modeling/v001/data/"
        >>> parse(pattern, path)
        {'task': 'modeling', 'version': 'v001'}

    Returns:
        dict: The data retrieved from path using pattern.
    """

    pattern = os.path.normpath(pattern)
    path = os.path.normpath(path)

    # Force forward slashes
    path = path.replace('\\', '/')
    pattern = pattern.replace('\\', '/')

    # Escape characters in path that are regex patterns so they are
    # excluded by the regex searches. Exclude '{' and '}' in escaping.
    pattern = re.escape(pattern)
    pattern = pattern.replace('\{', '{').replace('\}', '}')

    keys = re.findall(r'{(%s+)}' % RE_FILENAME,
                      pattern)
    if not keys:
        return []

    # Find the corresponding values
    value_pattern = re.sub(r'{(%s+)}' % RE_FILENAME,
                           r'(%s+)' % RE_FILENAME,
                           pattern)
    match_values = re.match(value_pattern, path)

    if not match_values:
        raise ParseError("Path doesn't match with pattern. No values parsed")

    values = match_values.groups()

    return dict(zip(keys, values))


def ls_iter(pattern, include=None, with_matches=False):
    """Yield all matches for the given pattern.

    If the pattern starts with a relative path (or a dynamic key) the search
    will start from the current working directory, defined by os.path.realpath.

    Arguments:
        pattern (str): The pattern to match and search against.
        include (dict): A dictionary used to target the search with the pattern
            to include only those key-value pairs within the pattern. With this
            you can reduce the filesystem query to a specified subset.

    Example:
        >>> data = {"root": "foobar", "content": "nugget"}
        >>> for path in ls_iter("{root}/{project}/data/{content}/",
        ...                     include=data):
        ...     print path

    Returns:
        (str, tuple): The matched paths (and data if `with_matches` is True)

        The returned value changes whether `with_matches` parameter is True or
        False. If True a 2-tuple is yielded for each match as (path, data) else
        only the path is returned
    """

    # format rule by data already provided to reduce query
    if include is not None:
        pattern = format(pattern, include, allow_partial=True)

    pattern = os.path.expandvars(pattern)
    pattern = os.path.realpath(pattern)

    glob_pattern = re.sub(r'([/\\]{\w+}[/\\])', '/*/', pattern)     # folder
    glob_pattern = re.sub(r'({\w+})', '*', glob_pattern)          # filename

    for path in glob.iglob(glob_pattern):
        path = os.path.realpath(path)
        if with_matches:
            data = parse(pattern, path)
            yield path, data
        else:
            yield path


def ls(pattern, include=None, with_matches=False):
    return list(ls_iter(pattern, include, with_matches=with_matches))


def _partial_format(s, data):
    """Return string `s` formatted by `data` allowing a partial format

    Arguments:
        s (str): The string that will be formatted
        data (dict): The dictionary used to format with.

    Example:
        >>> _partial_format("{d} {a} {b} {c} {d}", {'b': "and", 'd': "left"})
        'left {a} and {c} left'
    """

    class FormatDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    formatter = string.Formatter()
    mapping = FormatDict(**data)
    return formatter.vformat(s, (), mapping)
