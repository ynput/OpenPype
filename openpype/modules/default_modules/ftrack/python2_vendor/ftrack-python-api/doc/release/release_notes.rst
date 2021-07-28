..
    :copyright: Copyright (c) 2014 ftrack

.. _release/release_notes:

*************
Release Notes
*************

.. currentmodule:: ftrack_api.session

.. release:: 1.8.2
    :date: 2020-01-14

    .. change:: fixed
        :tag: Test

        test_ensure_entity_with_non_string_data_types test fails due to missing parents.

    .. change:: changed
        :tags: session

        Use WeakMethod when registering atexit handler to prevent memory leak.

.. release:: 1.8.1
    :date: 2019-10-30

    .. change:: changed
        :tags: Location

        Increase chunk size for file operations to 1 Megabyte.
        This value can now also be set from the environment variable:

        :envvar:`FTRACK_API_FILE_CHUNK_SIZE`

    .. change:: new
        :tag: setup

        Add check for correct python version when installing with pip.

    .. change:: new
        :tags: Notes

        Add support for note labels in create_note helper method.

    .. change:: changed
        :tags: session

        Ensure errors from server are fully reported with stack trace.

.. release:: 1.8.0
    :date: 2019-02-21

    .. change:: fixed
        :tags: documentation

        Event description component-removed report component-added event signature.

    .. change:: new
        :tags: session, attribute

        Add new scalar type `object` to factory.

    .. change:: new
        :tags: session, attribute

        Add support for list of `computed` attributes as part of schema
        definition. A computed attribute is derived on the server side, and can
        be time dependentant and differ between users. As such a computed
        attribute is not suitable for long term encoding and will not be encoded
        with the `persisted_only` stragey.

    .. change:: changed

        The `delayed_job` method has been deprecated in favour of a direct
        `Session.call`. See :ref:`example/sync_with_ldap` for example
        usage.

    .. change:: changed

        Private method :meth:`Session._call` has been converted to
        a public method, :meth:`Session.call`.

        The private method will continue to work, but a pending deprecation
        warning will be issued when used. The private method will be removed
        entirely in version 2.0.

    .. change:: changed
        :tags: session, events

        Event server connection error is too generic,
        the actual error is now reported to users.

.. release:: 1.7.1
    :date: 2018-11-13

    .. change:: fixed
        :tags: session, events

        Meta events for event hub connect and disconnect does not include
        source.

    .. change:: fixed
        :tags: session, location

        Missing context argument to
        :meth:`ResourceIdentifierTransformer.decode`
        in :meth:`Location.get_resource_identifier`.

.. release:: 1.7.0
    :date: 2018-07-27

    .. change:: new
        :tags: session, events

        Added new events :ref:`event_list/ftrack.api.session.ready` and
        :ref:`event_list/ftrack.api.session.reset` which can be used to perform
        operations after the session is ready or has been reset, respectively.

    .. change:: changed

        Private method :meth:`Session._entity_reference` has been converted to
        a public method, :meth:`Session.entity_reference`.

        The private method will continue to work, but a pending deprecation
        warning will be issued when used. The private method will be removed
        entirely in version 2.0.

    .. change:: fixed
        :tags: session, events

        :meth:`Session.close` raises an exception if event hub was explicitly
        connected after session initialization.

.. release:: 1.6.0
    :date: 2018-05-17

    .. change:: new
        :tags: depreciation, events

        In version 2.0.0 of the `ftrack-python-api` the default behavior for
        the :class:`Session` class will change for the argument
        *auto_connect_event_hub*, the default value will switch from *True* to
        *False*.

        A warning will now be emitted if async events are published or
        subscribed to without *auto_connect_event_hub* has not explicitly been
        set to *True*.

        .. seealso:: :ref:`release/migration/2.0.0/event_hub`.

    .. change:: fixed
        :tags: documentation

        Event payload not same as what is being emitted for
        :ref:`event_list/ftrack.location.component-added` and
        :ref:`event_list/ftrack.location.component-removed`.

    .. change:: fixed
        :tags: events

        Pyparsing is causing random errors in a threaded environment.

.. release:: 1.5.0
    :date: 2018-04-19

    .. change:: fixed
       :tags: session, cache

       Cached entities not updated correctly when fetched in a nested
       query.

.. release:: 1.4.0
    :date: 2018-02-05

    .. change:: fixed
        :tags: session, cache

        Collection attributes not merged correctly when fetched from
        server.

    .. change:: new
        :tags: session, user, api key

        New function :meth:`ftrack_api.session.Session.reset_remote` allows
        resetting of attributes to their default value. A convenience method
        for resetting a users api key utalizing this was also added
        :meth:`ftrack_api.entity.user.User.reset_api_key`.

        .. seealso:: :ref:`working_with_entities/resetting`

    .. change:: new

       Add support for sending out invitation emails to users.
       See :ref:`example/invite_user` for example usage.

    .. change:: changed
        :tags: cache, performance

        Entities fetched from cache are now lazily merged. Improved
        performance when dealing with highly populated caches.

.. release:: 1.3.3
    :date: 2017-11-16


    .. change:: new
        :tags: users, ldap

        Add support for triggering a synchronization of
        users between ldap and ftrack. See :ref:`example/sync_with_ldap`
        for example usage.

        .. note::

            This requires that you run ftrack 3.5.10 or later.

    .. change:: fixed
        :tags: metadata

        Not possible to set metadata on creation.

.. release:: 1.3.2
    :date: 2017-09-18


    .. change:: new
        :tags: task template

        Added example for managing task templates through the API. See
        :ref:`example/task_template` for example usage.

    .. change:: fixed
        :tags: custom attributes

         Not possible to set hierarchical custom attributes on an entity that
         has not been committed.

    .. change:: fixed
        :tags: custom attributes

         Not possible to set custom attributes on an `Asset` that has not been
         committed.

    .. change:: fixed
        :tags: metadata

        Not possible to set metadata on creation.

.. release:: 1.3.1
    :date: 2017-07-21

    .. change:: fixed
        :tags: session, events

        Calling disconnect on the event hub is slow.

.. release:: 1.3.0
    :date: 2017-07-17

    .. change:: new
        :tags: session

        Support using a :class:`Session` as a context manager to aid closing of
        session after use::

            with ftrack_api.Session() as session:
                # Perform operations with session.

    .. change:: new
        :tags: session

        :meth:`Session.close` automatically called on Python exit if session not
        already closed.

    .. change:: new
        :tags: session

        Added :meth:`Session.close` to properly close a session's connections to
        the server(s) as well as ensure event listeners are properly
        unsubscribed.

    .. change:: new

        Added :exc:`ftrack_api.exception.ConnectionClosedError` to represent
        error caused when trying to access servers over closed connection.

.. release:: 1.2.0
    :date: 2017-06-16

    .. change:: changed
        :tags: events

        Updated the websocket-client dependency to version >= 0.40.0 to allow
        for http proxies.

    .. change:: fixed
        :tags: documentation

        The :ref:`example/publishing` example incorrectly stated that a
        location would be automatically picked if the *location* keyword
        argument was omitted.

.. release:: 1.1.1
    :date: 2017-04-27

    .. change:: fixed
        :tags: custom attributes

        Cannot use custom attributes for `Asset` in ftrack versions prior to
        `3.5.0`.

    .. change:: fixed
        :tags: documentation

        The :ref:`example <example/manage_custom_attribute_configuration>`
        section for managing `text` custom attributes is not correct.

.. release:: 1.1.0
    :date: 2017-03-08

    .. change:: new
        :tags: server location, thumbnail

        Added method :meth:`get_thumbnail_url() <ftrack_api.entity.location.ServerLocationMixin.get_thumbnail_url>`
        to server location, which can be used to retrieve a thumbnail URL.
        See :ref:`example/thumbnail/url` for example usage.

    .. change:: new
        :tags: documentation

        Added :ref:`example <example/entity_links>` on how to manage entity
        links from the API.

    .. change:: new
        :tags: documentation

        Added :ref:`example <example/manage_custom_attribute_configuration>` on
        how to manage custom attribute configurations from the API.

    .. change:: new
        :tags: documentation

        Added :ref:`example <example/security_roles>` on how to use
        `SecurityRole` and `UserSecurityRole` to manage security roles for
        users.

    .. change:: new
        :tags: documentation

        Added :ref:`examples <example/assignments_and_allocations>` to show how
        to list a user's assigned tasks and all users assigned to a task.

    .. change:: changed
        :tags: session, plugins

        Added *plugin_arguments* to :class:`Session` to allow passing of
        optional keyword arguments to discovered plugin register functions. Only
        arguments defined in a plugin register function signature are passed so
        existing plugin register functions do not need updating if the new
        functionality is not desired.

    .. change:: fixed
        :tags: documentation

        The :ref:`example/project` example can be confusing since the project
        schema may not contain the necessary object types.

    .. change:: fixed
        :tags: documentation

        Query tutorial article gives misleading information about the ``has``
        operator.

    .. change:: fixed
        :tags: session

        Size is not set on sequence components when using
        :meth:`Session.create_component`.

.. release:: 1.0.4
    :date: 2017-01-13

    .. change:: fixed
        :tags: custom attributes

        Custom attribute values cannot be set on entities that are not
        persisted.

    .. change:: fixed
        :tags: events

        `username` in published event's source data is set to the operating
        system user and not the API user.

.. release:: 1.0.3
    :date: 2017-01-04

    .. change:: changed
        :tags: session, custom attributes

        Increased performance of custom attributes and better support for
        filtering when using a version of ftrack that supports non-sparse
        attribute values.

    .. change:: changed
        :tags: session, custom attributes

        Custom attributes can no longer be set by mutating entire dictionary.

        .. seealso:: :ref:`release/migration/1.0.3/mutating_dictionary`.

.. release:: 1.0.2
    :date: 2016-11-17

    .. change:: changed
        :tags: session

        Removed version restriction for higher server versions.

.. release:: 1.0.1
    :date: 2016-11-11

    .. change:: fixed

        :meth:`EventHub.publish <ftrack_api.event.hub.EventHub.publish>`
        *on_reply* callback only called for first received reply. It should be
        called for all relevant replies received.

.. release:: 1.0.0
    :date: 2016-10-28

    .. change:: new
        :tags: session

        :meth:`Session.get_upload_metadata` has been added.

    .. change:: changed
        :tags: locations, backwards-incompatible

        Data transfer between locations using accessors is now chunked to avoid
        reading large files into memory.

        .. seealso:: :ref:`release/migration/1.0.0/chunked_transfer`.

    .. change:: changed
        :tags: server accessor

        :class:`ftrack_api.accessor.server.ServerFile` has been refactored to
        work with large files more efficiently.

    .. change:: changed
        :tags: server accessor

        :class:`ftrack_api.accessor.server.ServerFile` has been updated to use
        the get_upload_metadata API endpoint instead of
        /component/getPutMetadata.

    .. change:: changed
        :tags: locations

        :class:`ftrack_api.data.String` is now using a temporary file instead of
        StringIO to avoid reading large files into memory.

    .. change:: fixed
        :tags: session, locations

        `ftrack.centralized-storage` does not properly validate location
        selection during user configuration.

.. release:: 0.16.0
    :date: 2016-10-18

    .. change:: new
        :tags: session, encode media

        :meth:`Session.encode_media` can now automatically associate the output
        with a version by specifying a *version_id* keyword argument. A new
        helper method on versions, :meth:`AssetVersion.encode_media
        <ftrack_api.entity.asset_version.AssetVersion.encode_media>`, can be
        used to make versions playable in a browser. A server version of 3.3.32
        or higher is required for it to function properly.

        .. seealso:: :ref:`example/encode_media`.

    .. change:: changed
        :tags: session, encode media

        You can now decide if :meth:`Session.encode_media` should keep or
        delete the original component by specifying the *keep_original*
        keyword argument.

    .. change:: changed
        :tags: backwards-incompatible, collection

        Collection mutation now stores collection instance in operations rather
        than underlying data structure.

    .. change:: changed
        :tags: performance

        Improve performance of commit operations by optimising encoding and
        reducing payload sent to server.

    .. change:: fixed
        :tags: documentation

        Asset parent variable is declared but never used in
        :ref:`example/publishing`.

    .. change:: fixed
        :tags: documentation

        Documentation of hierarchical attributes and their limitations are
        misleading. See :ref:`example/custom_attribute`.

.. release:: 0.15.5
    :date: 2016-08-12

    .. change:: new
        :tags: documentation

        Added two new examples for :ref:`example/publishing` and
        :ref:`example/web_review`.

    .. change:: fixed
        :tags: session, availability

        :meth:`Session.get_component_availabilities` ignores passed locations
        shortlist and includes all locations in returned availability mapping.

    .. change:: fixed
        :tags: documentation

        Source distribution of ftrack-python-api does not include ftrack.css
        in the documentation.

.. release:: 0.15.4
    :date: 2016-07-12

    .. change:: fixed
        :tags: querying

        Custom offset not respected by
        :meth:`QueryResult.first <ftrack_api.query.QueryResult.first>`.

    .. change:: changed
        :tags: querying

        Using a custom offset with :meth:`QueryResult.one
        <ftrack_api.query.QueryResult.one>` helper method now raises an
        exception as an offset is inappropriate when expecting to select a
        single item.

    .. change:: fixed
        :tags: caching

        :meth:`LayeredCache.remove <ftrack_api.cache.LayeredCache.remove>`
        incorrectly raises :exc:`~exceptions.KeyError` if key only exists in
        sub-layer cache.

.. release:: 0.15.3
    :date: 2016-06-30

    .. change:: fixed
        :tags: session, caching

        A newly created entity now has the correct
        :attr:`ftrack_api.symbol.CREATED` state when checked in caching layer.
        Previously the state was :attr:`ftrack_api.symbol.NOT_SET`. Note that
        this fix causes a change in logic and the stored
        :class:`ftrack_api.operation.CreateEntityOperation` might hold data that
        has not been fully :meth:`merged <Session.merge>`.

    .. change:: fixed
        :tags: documentation

        The second example in the assignments article is not working.

    .. change:: changed
        :tags: session, caching

        A callable cache maker can now return ``None`` to indicate that it could
        not create a suitable cache, but :class:`Session` instantiation can
        continue safely.

.. release:: 0.15.2
    :date: 2016-06-02

    .. change:: new
        :tags: documentation

        Added an example on how to work with assignments and allocations
        :ref:`example/assignments_and_allocations`.

    .. change:: new
        :tags: documentation

        Added :ref:`example/entity_links` article with
        examples of how to manage asset version dependencies.

    .. change:: fixed
        :tags: performance

        Improve performance of large collection management.

    .. change:: fixed

        Entities are not hashable because
        :meth:`ftrack_api.entity.base.Entity.__hash__` raises `TypeError`.

.. release:: 0.15.1
    :date: 2016-05-02

    .. change:: fixed
        :tags: collection, attribute, performance

        Custom attribute configurations does not cache necessary keys, leading
        to performance issues.

    .. change:: fixed
        :tags: locations, structure

        Standard structure does not work if version relation is not set on
        the `Component`.

.. release:: 0.15.0
    :date: 2016-04-04

    .. change:: new
        :tags: session, locations

        `ftrack.centralized-storage` not working properly on Windows.

.. release:: 0.14.0
    :date: 2016-03-14

    .. change:: changed
        :tags: session, locations

        The `ftrack.centralized-storage` configurator now validates that name,
        label and description for new locations are filled in.

    .. change:: new
        :tags: session, client review

        Added :meth:`Session.send_review_session_invite` and
        :meth:`Session.send_review_session_invites` that can be used to inform
        review session invitees about a review session.

        .. seealso:: :ref:`Usage guide <example/review_session>`.

    .. change:: new
        :tags: session, locations

        Added `ftrack.centralized-storage` configurator as a private module. It
        implements a wizard like interface used to configure a centralised
        storage scenario.

    .. change:: new
        :tags: session, locations

        `ftrack.centralized-storage` storage scenario is automatically
        configured based on information passed from the server with the
        `query_server_information` action.

    .. change:: new
        :tags: structure

        Added :class:`ftrack_api.structure.standard.StandardStructure` with
        hierarchy based resource identifier generation.

    .. change:: new
        :tags: documentation

        Added more information to the :ref:`understanding_sessions/plugins`
        article.

    .. change:: fixed

        :meth:`~ftrack_api.entity.user.User.start_timer` arguments *comment*
        and *name* are ignored.

    .. change:: fixed

        :meth:`~ftrack_api.entity.user.User.stop_timer` calculates the wrong
        duration when the server is not running in UTC.

        For the duration to be calculated correctly ftrack server version
        >= 3.3.15 is required.

.. release:: 0.13.0
    :date: 2016-02-10

    .. change:: new
        :tags: component, thumbnail

        Added improved support for handling thumbnails.

        .. seealso:: :ref:`example/thumbnail`.

    .. change:: new
        :tags: session, encode media

        Added :meth:`Session.encode_media` that can be used to encode
        media to make it playable in a browser.

        .. seealso:: :ref:`example/encode_media`.

    .. change:: fixed

        :meth:`Session.commit` fails when setting a custom attribute on an asset
        version that has been created and committed in the same session.

    .. change:: new
        :tags: locations

        Added :meth:`ftrack_api.entity.location.Location.get_url` to retrieve a
        URL to a component in a location if supported by the
        :class:`ftrack_api.accessor.base.Accessor`.

    .. change:: new
        :tags: documentation

        Updated :ref:`example/note` and :ref:`example/job` articles with
        examples of how to use note and job components.

    .. change:: changed
        :tags: logging, performance

        Logged messages now evaluated lazily using
        :class:`ftrack_api.logging.LazyLogMessage` as optimisation.

    .. change:: changed
        :tags: session, events

        Auto connection of event hub for :class:`Session` now takes place in
        background to improve session startup time.

    .. change:: changed
        :tags: session, events

        Event hub connection timeout is now 60 seconds instead of 10.

    .. change:: changed
        :tags: server version

        ftrack server version >= 3.3.11, < 3.4 required.

    .. change:: changed
        :tags: querying, performance

        :class:`ftrack_api.query.QueryResult` now pages internally using a
        specified page size in order to optimise record retrieval for large
        query results. :meth:`Session.query` has also been updated to allow
        passing a custom page size at runtime if desired.

    .. change:: changed
        :tags: querying, performance

        Increased performance of :meth:`~ftrack_api.query.QueryResult.first` and
        :meth:`~ftrack_api.query.QueryResult.one` by using new `limit` syntax.

.. release:: 0.12.0
    :date: 2015-12-17

    .. change:: new
        :tags: session, widget url

        Added :meth:`ftrack_api.session.Session.get_widget_url` to retrieve an
        authenticated URL to info or tasks widgets.

.. release:: 0.11.0
    :date: 2015-12-04

    .. change:: new
        :tags: documentation

        Updated :ref:`release/migrating_from_old_api` with new link attribute
        and added a :ref:`usage example <example/link_attribute>`.

    .. change:: new
        :tags: caching, schemas, performance

        Caching of schemas for increased performance.
        :meth:`ftrack_api.session.Session` now accepts `schema_cache_path`
        argument to specify location of schema cache. If not set it will use a
        temporary folder.

.. release:: 0.10.0
    :date: 2015-11-24

    .. change:: changed
        :tags: tests

        Updated session test to use mocked schemas for encoding tests.

    .. change:: fixed

        Documentation specifies Python 2.6 instead of Python 2.7 as minimum
        interpreter version.

    .. change:: fixed

        Documentation does not reflect current dependencies.

    .. change:: changed
        :tags: session, component, locations, performance

        Improved performance of
        :meth:`ftrack_api.entity.location.Location.add_components` by batching
        database operations.

        As a result it is no longer possible to determine progress of transfer
        for container components in realtime as events will be emitted in batch
        at end of operation.

        In addition, it is now the callers responsibility to clean up any
        transferred data should an error occur during either data transfer or
        database registration.

    .. change:: changed
        :tags: exception, locations

        :exc:`ftrack_api.exception.ComponentInLocationError` now accepts either
        a single component or multiple components and makes them available as
        *components* in its *details* parameter.

    .. change:: changed
        :tags: tests

        Updated session test to not fail on the new private link attribute.

    .. change:: changed
        :tags: session

        Internal method :py:meth:`_fetch_schemas` has beed renamed to
        :py:meth:`Session._load_schemas` and now requires a `schema_cache_path`
        argument.

.. release:: 0.9.0
    :date: 2015-10-30

    .. change:: new
        :tags: caching

        Added :meth:`ftrack_api.cache.Cache.values` as helper for retrieving
        all values in cache.

    .. change:: fixed
        :tags: session, caching

        :meth:`Session.merge` redundantly attempts to expand entity references
        that have already been expanded causing performance degradation.

    .. change:: new
        :tags: session

        :meth:`Session.rollback` has been added to support cleanly reverting
        session state to last good state following a failed commit.

    .. change:: changed
        :tags: events

        Event hub will no longer allow unverified SSL connections.

        .. seealso:: :ref:`security_and_authentication`.

    .. change:: changed
        :tags: session

        :meth:`Session.reset` no longer resets the connection. It also clears
        all local state and re-configures certain aspects that are cache
        dependant, such as location plugins.

    .. change:: fixed
        :tags: factory

        Debug logging messages using incorrect index for formatting leading to
        misleading exception.

.. release:: 0.8.4
    :date: 2015-10-08

    .. change:: new

        Added initial support for custom attributes.

        .. seealso:: :ref:`example/custom_attribute`.

    .. change:: new
        :tags: collection, attribute

        Added :class:`ftrack_api.collection.CustomAttributeCollectionProxy` and
        :class:`ftrack_api.attribute.CustomAttributeCollectionAttribute` to
        handle custom attributes.

    .. change:: changed
        :tags: collection, attribute

        ``ftrack_api.attribute.MappedCollectionAttribute`` renamed to
        :class:`ftrack_api.attribute.KeyValueMappedCollectionAttribute` to more
        closely reflect purpose.

    .. change:: changed
        :tags: collection

        :class:`ftrack_api.collection.MappedCollectionProxy` has been refactored
        as a generic base class with key, value specialisation handled in new
        dedicated class
        :class:`ftrack_api.collection.KeyValueMappedCollectionProxy`. This is
        done to avoid confusion following introduction of new
        :class:`ftrack_api.collection.CustomAttributeCollectionProxy` class.

    .. change:: fixed
        :tags: events

        The event hub does not always reconnect after computer has come back
        from sleep.

.. release:: 0.8.3
    :date: 2015-09-28

    .. change:: changed
        :tags: server version

        ftrack server version >= 3.2.1, < 3.4 required.

    .. change:: changed

        Updated *ftrack.server* location implementation. A server version of 3.3
        or higher is required for it to function properly.

    .. change:: fixed

        :meth:`ftrack_api.entity.factory.StandardFactory.create` not respecting
        *bases* argument.

.. release:: 0.8.2
    :date: 2015-09-16

    .. change:: fixed
        :tags: session

        Wrong file type set on component when publishing image sequence using
        :meth:`Session.create_component`.

.. release:: 0.8.1
    :date: 2015-09-08

    .. change:: fixed
        :tags: session

        :meth:`Session.ensure` not implemented.

.. release:: 0.8.0
    :date: 2015-08-28

    .. change:: changed
        :tags: server version

        ftrack server version >= 3.2.1, < 3.3 required.

    .. change:: new

        Added lists example.

            .. seealso:: :ref:`example/list`.

    .. change:: new

        Added convenience methods for handling timers
        :class:`~ftrack_api.entity.user.User.start_timer` and
        :class:`~ftrack_api.entity.user.User.stop_timer`.

    .. change:: changed

        The dynamic API classes Type, Status, Priority and
        StatusType have been renamed to Type, Status, Priority and State.

    .. change:: changed

        :meth:`Session.reset` now also clears the top most level cache (by
        default a :class:`~ftrack_api.cache.MemoryCache`).

    .. change:: fixed

        Some invalid server url formats not detected.

    .. change:: fixed

        Reply events not encoded correctly causing them to be misinterpreted by
        the server.

.. release:: 0.7.0
    :date: 2015-08-24

    .. change:: changed
        :tags: server version

        ftrack server version >= 3.2, < 3.3 required.

    .. change:: changed

        Removed automatic set of default statusid, priorityid and typeid on
        objects as that is now either not mandatory or handled on server.

    .. change:: changed

        Updated :meth:`~ftrack_api.entity.project_schema.ProjectSchema.get_statuses`
        and :meth:`~ftrack_api.entity.project_schema.ProjectSchema.get_types` to
        handle custom objects.

.. release:: 0.6.0
    :date: 2015-08-19

    .. change:: changed
        :tags: server version

        ftrack server version >= 3.1.8, < 3.2 required.

    .. change:: changed
        :tags: querying, documentation

        Updated documentation with details on new operators ``has`` and ``any``
        for querying relationships.

        .. seealso:: :ref:`querying/criteria/operators`

.. release:: 0.5.2
    :date: 2015-07-29

    .. change:: changed
        :tags: server version

        ftrack server version 3.1.5 or greater required.

    .. change:: changed

        Server reported errors are now more readable and are no longer sometimes
        presented as an HTML page.

.. release:: 0.5.1
    :date: 2015-07-06

    .. change:: changed

        Defaults computed by :class:`~ftrack_api.entity.factory.StandardFactory`
        are now memoised per session to improve performance.

    .. change:: changed

        :class:`~ftrack_api.cache.Memoiser` now supports a *return_copies*
        parameter to control whether deep copies should be returned when a value
        was retrieved from the cache.

.. release:: 0.5.0
    :date: 2015-07-02

    .. change:: changed

        Now checks for server compatibility and requires an ftrack server
        version of 3.1 or greater.

    .. change:: new

        Added convenience methods to :class:`~ftrack_api.query.QueryResult` to
        fetch :meth:`~ftrack_api.query.QueryResult.first` or exactly
        :meth:`~ftrack_api.query.QueryResult.one` result.

    .. change:: new
        :tags: notes

        Added support for handling notes.

        .. seealso:: :ref:`example/note`.

    .. change:: changed

        Collection attributes generate empty collection on first access when no
        remote value available. This allows interacting with a collection on a
        newly created entity before committing.

    .. change:: fixed
        :tags: session

        Ambiguous error raised when :class:`Session` is started with an invalid
        user or key.

    .. change:: fixed
        :tags: caching, session

        :meth:`Session.merge` fails against
        :class:`~ftrack_api.cache.SerialisedCache` when circular reference
        encountered due to entity identity not being prioritised in merge.

.. release:: 0.4.3
    :date: 2015-06-29

    .. change:: fixed
        :tags: plugins, session, entity types

        Entity types not constructed following standard install.

        This is because the discovery of the default plugins is unreliable
        across Python installation processes (pip, wheel etc). Instead, the
        default plugins have been added as templates to the :ref:`event_list`
        documentation and the
        :class:`~ftrack_api.entity.factory.StandardFactory` used to create any
        missing classes on :class:`Session` startup.

.. release:: 0.4.2
    :date: 2015-06-26

    .. change:: fixed
        :tags: metadata

        Setting exact same metadata twice can cause
        :exc:`~ftrack_api.exception.ImmutableAttributeError` to be incorrectly
        raised.

    .. change:: fixed
        :tags: session

        Calling :meth:`Session.commit` does not clear locally set attribute
        values leading to immutability checks being bypassed in certain cases.

.. release:: 0.4.1
    :date: 2015-06-25

    .. change:: fixed
        :tags: metadata

        Setting metadata twice in one session causes `KeyError`.

.. release:: 0.4.0
    :date: 2015-06-22

    .. change:: changed
        :tags: documentation

        Documentation extensively updated.

    .. change:: new
        :tags: Client review

        Added support for handling review sessions.

        .. seealso:: :ref:`Usage guide <example/review_session>`.

    .. change:: fixed

        Metadata property not working in line with rest of system, particularly
        the caching framework.

    .. change:: new
        :tags: collection

        Added :class:`ftrack_api.collection.MappedCollectionProxy` class for
        providing a dictionary interface to a standard
        :class:`ftrack_api.collection.Collection`.

    .. change:: new
        :tags: collection, attribute

        Added :class:`ftrack_api.attribute.MappedCollectionAttribute` class for
        describing an attribute that should use the
        :class:`ftrack_api.collection.MappedCollectionProxy`.

    .. change:: new

        Entities that use composite primary keys are now fully supported in the
        session, including for :meth:`Session.get` and :meth:`Session.populate`.

    .. change:: change

        Base :class:`ftrack_api.entity.factory.Factory` refactored to separate
        out attribute instantiation into dedicated methods to make extending
        simpler.

    .. change:: change
        :tags: collection, attribute

        :class:`ftrack_api.attribute.DictionaryAttribute` and
        :class:`ftrack_api.attribute.DictionaryAttributeCollection` removed.
        They have been replaced by the new
        :class:`ftrack_api.attribute.MappedCollectionAttribute` and
        :class:`ftrack_api.collection.MappedCollectionProxy` respectively.

    .. change:: new
        :tags: events

        :class:`Session` now supports an *auto_connect_event_hub* argument to
        control whether the built in event hub should connect to the server on
        session initialisation. This is useful for when only local events should
        be supported or when the connection should be manually controlled.

.. release:: 0.3.0
    :date: 2015-06-14

    .. change:: fixed

        Session operations may be applied server side in invalid order resulting
        in unexpected error.

    .. change:: fixed

        Creating and deleting an entity in single commit causes error as create
        operation never persisted to server.

        Now all operations for the entity are ignored on commit when this case
        is detected.

    .. change:: changed

        Internally moved from differential state to operation tracking for
        determining session changes when persisting.

    .. change:: new

        ``Session.recorded_operations`` attribute for examining current
        pending operations on a :class:`Session`.

    .. change:: new

        :meth:`Session.operation_recording` context manager for suspending
        recording operations temporarily. Can also manually control
        ``Session.record_operations`` boolean.

    .. change:: new

        Operation classes to track individual operations occurring in session.

    .. change:: new

        Public :meth:`Session.merge` method for merging arbitrary values into
        the session manually.

    .. change:: changed

        An entity's state is now computed from the operations performed on it
        and is no longer manually settable.

    .. change:: changed

        ``Entity.state`` attribute removed. Instead use the new inspection
        :func:`ftrack_api.inspection.state`.

        Previously::

            print entity.state

        Now::

            import ftrack_api.inspection
            print ftrack_api.inspection.state(entity)

        There is also an optimised inspection,
        :func:`ftrack_api.inspection.states`. for determining state of many
        entities at once.

    .. change:: changed

        Shallow copying a :class:`ftrack_api.symbol.Symbol` instance now
        returns same instance.

.. release:: 0.2.0
    :date: 2015-06-04

    .. change:: changed

        Changed name of API from `ftrack` to `ftrack_api`.

        .. seealso:: :ref:`release/migration/0.2.0/new_api_name`.

    .. change:: new
        :tags: caching

        Configurable caching support in :class:`Session`, including the ability
        to use an external persisted cache and new cache implementations.

        .. seealso:: :ref:`caching`.

    .. change:: new
        :tags: caching

        :meth:`Session.get` now tries to retrieve matching entity from
        configured cache first.

    .. change:: new
        :tags: serialisation, caching

        :meth:`Session.encode` supports a new mode *persisted_only* that will
        only encode persisted attribute values.

    .. change:: changed

        Session.merge method is now private (:meth:`Session._merge`) until it is
        qualified for general usage.

    .. change:: changed
        :tags: entity state

        :class:`~ftrack_api.entity.base.Entity` state now managed on the entity
        directly rather than stored separately in the :class:`Session`.

        Previously::

            session.set_state(entity, state)
            print session.get_state(entity)

        Now::

            entity.state = state
            print entity.state

    .. change:: changed
        :tags: entity state

        Entity states are now :class:`ftrack_api.symbol.Symbol` instances rather
        than strings.

        Previously::

            entity.state = 'created'

        Now::

            entity.state = ftrack_api.symbol.CREATED

    .. change:: fixed
        :tags: entity state

        It is now valid to transition from most entity states to an
        :attr:`ftrack_api.symbol.NOT_SET` state.

    .. change:: changed
        :tags: caching

        :class:`~ftrack_api.cache.EntityKeyMaker` removed and replaced by
        :class:`~ftrack_api.cache.StringKeyMaker`. Entity identity now
        computed separately and passed to key maker to allow key maker to work
        with non entity instances.

    .. change:: fixed
        :tags: entity

        Internal data keys ignored when re/constructing entities reducing
        distracting and irrelevant warnings in logs.

    .. change:: fixed
        :tags: entity

        :class:`~ftrack_api.entity.base.Entity` equality test raises error when
        other is not an entity instance.

    .. change:: changed
        :tags: entity, caching

        :meth:`~ftrack_api.entity.base.Entity.merge` now also merges state and
        local attributes. In addition, it ensures values being merged have also
        been merged into the session and outputs more log messages.

    .. change:: fixed
        :tags: inspection

        :func:`ftrack_api.inspection.identity` returns different result for same
        entity depending on whether entity type is unicode or string.

    .. change:: fixed

        :func:`ftrack_api.mixin` causes method resolution failure when same
        class mixed in multiple times.

    .. change:: changed

        Representations of objects now show plain id rather than converting to
        hex.

    .. change:: fixed
        :tags: events

        Event hub raises TypeError when listening to ftrack.update events.

    .. change:: fixed
        :tags: events

        :meth:`ftrack_api.event.hub.EventHub.subscribe` fails when subscription
        argument contains special characters such as `@` or `+`.

    .. change:: fixed
        :tags: collection

        :meth:`ftrack_api.collection.Collection` incorrectly modifies entity
        state on initialisation.

.. release:: 0.1.0
    :date: 2015-03-25

    .. change:: changed

        Moved standardised construct entity type logic to core package (as part
        of the :class:`~ftrack_api.entity.factory.StandardFactory`) for easier
        reuse and extension.

.. release:: 0.1.0-beta.2
    :date: 2015-03-17

    .. change:: new
        :tags: locations

        Support for ftrack.server location. The corresponding server build is
        required for it to function properly.

    .. change:: new
        :tags: locations

        Support for managing components in locations has been added. Check out
        the :ref:`dedicated tutorial <locations/tutorial>`.

    .. change:: new

        A new inspection API (:mod:`ftrack_api.inspection`) has been added for
        extracting useful information from objects in the system, such as the
        identity of an entity.

    .. change:: changed

        ``Entity.primary_key`` and ``Entity.identity`` have been removed.
        Instead, use the new :func:`ftrack_api.inspection.primary_key` and
        :func:`ftrack_api.inspection.identity` functions. This was done to make it
        clearer the the extracted information is determined from the current
        entity state and modifying the returned object will have no effect on
        the entity instance itself.

    .. change:: changed

        :func:`ftrack_api.inspection.primary_key` now returns a mapping of the
        attribute names and values that make up the primary key, rather than
        the previous behaviour of returning a tuple of just the values. To
        emulate previous behaviour do::

            ftrack_api.inspection.primary_key(entity).values()

    .. change:: changed

        :meth:`Session.encode` now supports different strategies for encoding
        entities via the entity_attribute_strategy* keyword argument. This makes
        it possible to use this method for general serialisation of entity
        instances.

    .. change:: changed

        Encoded referenced entities are now a mapping containing
        *__entity_type__* and then each key, value pair that makes up the
        entity's primary key. For example::

            {
                '__entity_type__': 'User',
                'id': '8b90a444-4e65-11e1-a500-f23c91df25eb'
            }

    .. change:: changed

        :meth:`Session.decode` no longer automatically adds decoded entities to
        the :class:`Session` cache making it possible to use decode
        independently.

    .. change:: new

        Added :meth:`Session.merge` for merging entities recursively into the
        session cache.

    .. change:: fixed

        Replacing an entity in a :class:`ftrack_api.collection.Collection` with an
        identical entity no longer raises
        :exc:`ftrack_api.exception.DuplicateItemInCollectionError`.
