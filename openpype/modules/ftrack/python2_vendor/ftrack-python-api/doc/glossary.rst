..
    :copyright: Copyright (c) 2014 ftrack

********
Glossary
********

.. glossary::

    accessor
        An implementation (typically a :term:`Python` plugin) for accessing
        a particular type of storage using a specific protocol.

        .. seealso:: :ref:`locations/overview/accessors`

    action
        Actions in ftrack provide a standardised way to integrate other tools,
        either off-the-shelf or custom built, directly into your ftrack
        workflow.

        .. seealso:: :ref:`ftrack:using/actions`

    api
        Application programming interface.

    arrow
        A Python library that offers a sensible, human-friendly approach to 
        creating, manipulating, formatting and converting dates, times, and
        timestamps. Read more at http://crsmithdev.com/arrow/

    asset
        A container for :term:`asset versions <asset version>`, typically
        representing the output from an artist. For example, 'geometry'
        from a modeling artist. Has an :term:`asset type` that categorises the
        asset.

    asset type
        Category for a particular asset.

    asset version
        A specific version of data for an :term:`asset`. Can contain multiple
        :term:`components <component>`.

    component
        A container to hold any type of data (such as a file or file sequence).
        An :term:`asset version` can have any number of components, each with
        a specific name. For example, a published version of geometry might
        have two components containing the high and low resolution files, with
        the component names as 'hires' and 'lowres' respectively.

    PEP-8
        Style guide for :term:`Python` code. Read the guide at 
        https://www.python.org/dev/peps/pep-0008/

    plugin
        :term:`Python` plugins are used by the API to extend it with new
        functionality, such as :term:`locations <location>` or :term:`actions <action>`.

        .. seealso:: :ref:`understanding_sessions/plugins`

    python
        A programming language that lets you work more quickly and integrate
        your systems more effectively. Often used in creative industries. Visit
        the language website at http://www.python.org

    PyPi
        :term:`Python` package index. The Python Package Index or PyPI is the
        official third-party software repository for the Python programming
        language. Visit the website at https://pypi.python.org/pypi

    resource identifier
        A string that is stored in ftrack as a reference to a resource (such as
        a file) in a specific location. Used by :term:`accessors <accessor>` to
        determine how to access data.

        .. seealso:: :ref:`locations/overview/resource_identifiers`
