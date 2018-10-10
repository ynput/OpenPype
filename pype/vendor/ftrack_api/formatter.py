# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

from builtins import str
import termcolor

import ftrack_api.entity.base
import ftrack_api.collection
import ftrack_api.symbol
import ftrack_api.inspection


#: Useful filters to pass to :func:`format`.`
FILTER = {
    'ignore_unset': (
        lambda entity, name, value: value is not ftrack_api.symbol.NOT_SET
    )
}


def format(
    entity, formatters=None, attribute_filter=None, recursive=False,
    indent=0, indent_first_line=True, _seen=None
):
    '''Return formatted string representing *entity*.

    *formatters* can be used to customise formatting of elements. It should be a
    mapping with one or more of the following keys:

        * header - Used to format entity type.
        * label - Used to format attribute names.

    Specify an *attribute_filter* to control which attributes to include. By
    default all attributes are included. The *attribute_filter* should be a
    callable that accepts `(entity, attribute_name, attribute_value)` and
    returns True if the attribute should be included in the output. For example,
    to filter out all unset values::

        attribute_filter=ftrack_api.formatter.FILTER['ignore_unset']

    If *recursive* is True then recurse into Collections and format each entity
    present.

    *indent* specifies the overall indentation in spaces of the formatted text,
    whilst *indent_first_line* determines whether to apply that indent to the
    first generated line.

    .. warning::

        Iterates over all *entity* attributes which may cause multiple queries
        to the server. Turn off auto populating in the session to prevent this.

    '''
    # Initialise default formatters.
    if formatters is None:
        formatters = dict()

    formatters.setdefault(
        'header', lambda text: termcolor.colored(
            text, 'white', 'on_blue', attrs=['bold']
        )
    )
    formatters.setdefault(
        'label', lambda text: termcolor.colored(
            text, 'blue', attrs=['bold']
        )
    )

    # Determine indents.
    spacer = ' ' * indent
    if indent_first_line:
        first_line_spacer = spacer
    else:
        first_line_spacer = ''

    # Avoid infinite recursion on circular references.
    if _seen is None:
        _seen = set()

    identifier = str(ftrack_api.inspection.identity(entity))
    if identifier in _seen:
        return (
            first_line_spacer +
            formatters['header'](entity.entity_type) + '{...}'
        )

    _seen.add(identifier)
    information = list()

    information.append(
        first_line_spacer + formatters['header'](entity.entity_type)
    )
    for key, value in sorted(entity.items()):
        if attribute_filter is not None:
            if not attribute_filter(entity, key, value):
                continue

        child_indent = indent + len(key) + 3

        if isinstance(value, ftrack_api.entity.base.Entity):
            value = format(
                value,
                formatters=formatters,
                attribute_filter=attribute_filter,
                recursive=recursive,
                indent=child_indent,
                indent_first_line=False,
                _seen=_seen.copy()
            )

        if isinstance(value, ftrack_api.collection.Collection):
            if recursive:
                child_values = []
                for index, child in enumerate(value):
                    child_value = format(
                        child,
                        formatters=formatters,
                        attribute_filter=attribute_filter,
                        recursive=recursive,
                        indent=child_indent,
                        indent_first_line=index != 0,
                        _seen=_seen.copy()
                    )
                    child_values.append(child_value)

                value = '\n'.join(child_values)

        information.append(
            spacer + u' {0}: {1}'.format(formatters['label'](key), value)
        )

    return '\n'.join(information)
