..
    :copyright: Copyright (c) 2014 ftrack

.. _environment_variables:

*********************
Environment variables
*********************

The following is a consolidated list of environment variables that this API
can reference:

.. envvar:: FTRACK_SERVER

    The full url of the ftrack server to connect to. For example
    "https://mycompany.ftrackapp.com"

.. envvar:: FTRACK_API_USER

    The username of the ftrack user to act on behalf of when performing actions
    in the system.

    .. note::

        When this environment variable is not set, the API will typically also
        check other standard operating system variables that hold the username
        of the current logged in user. To do this it uses
        :func:`getpass.getuser`.

.. envvar:: FTRACK_API_KEY

    The API key to use when performing actions in the system. The API key is
    used to determine the permissions that a script has in the system.

.. envvar:: FTRACK_APIKEY

    For backwards compatibility. See :envvar:`FTRACK_API_KEY`.

.. envvar:: FTRACK_EVENT_PLUGIN_PATH

    Paths to search recursively for plugins to load and use in a session.
    Multiple paths can be specified by separating with the value of
    :attr:`os.pathsep` (e.g. ':' or ';').

.. envvar:: FTRACK_API_SCHEMA_CACHE_PATH

    Path to a directory that will be used for storing and retrieving a cache of
    the entity schemas fetched from the server.

.. envvar:: http_proxy / https_proxy

    If you need to use a proxy to connect to ftrack you can use the
    "standard" :envvar:`http_proxy` and :envvar:`https_proxy`. Please note that they
    are lowercase.

    For example "export https_proxy=http://proxy.mycompany.com:8080"