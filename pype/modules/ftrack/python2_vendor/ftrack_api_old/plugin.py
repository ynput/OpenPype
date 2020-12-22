# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

from __future__ import absolute_import

import logging
import os
import uuid
import imp
import inspect


def discover(paths, positional_arguments=None, keyword_arguments=None):
    '''Find and load plugins in search *paths*.

    Each discovered module should implement a register function that accepts
    *positional_arguments* and *keyword_arguments* as \*args and \*\*kwargs
    respectively.

    If a register function does not accept variable arguments, then attempt to
    only pass accepted arguments to the function by inspecting its signature.

    '''
    logger = logging.getLogger(__name__ + '.discover')

    if positional_arguments is None:
        positional_arguments = []

    if keyword_arguments is None:
        keyword_arguments = {}

    for path in paths:
        # Ignore empty paths that could resolve to current directory.
        path = path.strip()
        if not path:
            continue

        for base, directories, filenames in os.walk(path):
            for filename in filenames:
                name, extension = os.path.splitext(filename)
                if extension != '.py':
                    continue

                module_path = os.path.join(base, filename)
                unique_name = uuid.uuid4().hex

                try:
                    module = imp.load_source(unique_name, module_path)
                except Exception as error:
                    logger.warning(
                        'Failed to load plugin from "{0}": {1}'
                        .format(module_path, error)
                    )
                    continue

                try:
                    module.register
                except AttributeError:
                    logger.warning(
                        'Failed to load plugin that did not define a '
                        '"register" function at the module level: {0}'
                        .format(module_path)
                    )
                else:
                    # Attempt to only pass arguments that are accepted by the
                    # register function.
                    specification = inspect.getargspec(module.register)

                    selected_positional_arguments = positional_arguments
                    selected_keyword_arguments = keyword_arguments

                    if (
                        not specification.varargs and
                        len(positional_arguments) > len(specification.args)
                    ):
                        logger.warning(
                            'Culling passed arguments to match register '
                            'function signature.'
                        )

                        selected_positional_arguments = positional_arguments[
                            len(specification.args):
                        ]
                        selected_keyword_arguments = {}

                    elif not specification.keywords:
                        # Remove arguments that have been passed as positionals.
                        remainder = specification.args[
                            len(positional_arguments):
                        ]

                        # Determine remaining available keyword arguments.
                        defined_keyword_arguments = []
                        if specification.defaults:
                            defined_keyword_arguments = specification.args[
                                -len(specification.defaults):
                            ]

                        remaining_keyword_arguments = set([
                            keyword_argument for keyword_argument
                            in defined_keyword_arguments
                            if keyword_argument in remainder
                        ])

                        if not set(keyword_arguments.keys()).issubset(
                            remaining_keyword_arguments
                        ):
                            logger.warning(
                                'Culling passed arguments to match register '
                                'function signature.'
                            )
                            selected_keyword_arguments = {
                                key: value
                                for key, value in keyword_arguments.items()
                                if key in remaining_keyword_arguments
                            }

                    module.register(
                        *selected_positional_arguments,
                        **selected_keyword_arguments
                    )
