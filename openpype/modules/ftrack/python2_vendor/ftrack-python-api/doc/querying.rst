..
    :copyright: Copyright (c) 2014 ftrack

.. _querying:

********
Querying
********

.. currentmodule:: ftrack_api.session

The API provides a simple, but powerful query language in addition to iterating
directly over entity attributes. Using queries can often substantially speed
up your code as well as reduce the amount of code written.

A query is issued using :meth:`Session.query` and returns a list of matching
entities. The query always has a single *target* entity type that the query
is built against. This means that you cannot currently retrieve back a list of
different entity types in one query, though using :ref:`projections
<querying/projections>` does allow retrieving related entities of a different
type in one go.

The syntax for a query is:

.. code-block:: none

    select <projections> from <entity type> where <criteria>

However, both the selection of projections and criteria are optional. This means
the most basic query is just to fetch all entities of a particular type, such as
all projects in the system::

    projects = session.query('Project')

A query always returns a :class:`~ftrack_api.query.QueryResult` instance that
acts like a list with some special behaviour. The main special behaviour is that
the actual query to the server is not issued until you iterate or index into the
query results::

    for project in projects:
        print project['name']

You can also explicitly call :meth:`~ftrack_api.query.QueryResult.all` on the
result set::

    projects = session.query('Project').all()

.. note::

    This behaviour exists in order to make way for efficient *paging* and other
    optimisations in future.

.. _querying/criteria:

Using criteria to narrow results
================================

Often you will have some idea of the entities you want to retrieve. In this
case you can optimise your code by not fetching more data than you need. To do
this, add criteria to your query::

    projects = session.query('Project where status is active')

Each criteria follows the form:

.. code-block:: none

    <attribute> <operator> <value>

You can inspect the entity type or instance to find out which :ref:`attributes
<working_with_entities/attributes>` are available to filter on for a particular
entity type. The list of :ref:`operators <querying/criteria/operators>` that can
be applied and the types of values they expect is listed later on.

.. _querying/criteria/combining:

Combining criteria
------------------

Multiple criteria can be applied in a single expression by joining them with
either ``and`` or ``or``::

    projects = session.query(
        'Project where status is active and name like "%thrones"'
    )

You can use parenthesis to control the precedence when compound criteria are
used (by default ``and`` takes precedence)::

    projects = session.query(
        'Project where status is active and '
        '(name like "%thrones" or full_name like "%thrones")'
    )

.. _querying/criteria/relationships:

Filtering on relationships
--------------------------

Filtering on relationships is also intuitively supported. Simply follow the
relationship using a dotted notation::

    tasks_in_project = session.query(
        'Task where project.id is "{0}"'.format(project['id'])
    )

This works even for multiple strides across relationships (though do note that
excessive strides can affect performance)::

    tasks_completed_in_project = session.query(
        'Task where project.id is "{0}" and '
        'status.type.name is "Done"'
        .format(project['id'])
    )

The same works for collections (where each entity in the collection is compared
against the subsequent condition)::

    import arrow

    tasks_with_time_logged_today = session.query(
        'Task where timelogs.start >= "{0}"'.format(arrow.now().floor('day'))
    )

In the above query, each *Task* that has at least one *Timelog* with a *start*
time greater than the start of today is returned.

When filtering on relationships, the conjunctions ``has`` and ``any`` can be
used to specify how the criteria should be applied. This becomes important when
querying using multiple conditions on collection relationships. The relationship
condition can be written against the following form::

    <not?> <relationship> <has|any> (<criteria>)

For optimal performance ``has`` should be used for scalar relationships when
multiple conditions are involved. For example, to find notes by a specific
author when only name is known::

    notes_written_by_jane_doe = session.query(
        'Note where author has (first_name is "Jane" and last_name is "Doe")'
    )

This query could be written without ``has``, giving the same results::

    notes_written_by_jane_doe = session.query(
        'Note where author.first_name is "Jane" and author.last_name is "Doe"'
    )

``any`` should be used for collection relationships. For example, to find all
projects that have at least one metadata instance that has `key=some_key` 
and `value=some_value` the query would be::

    projects_where_some_key_is_some_value = session.query(
        'Project where metadata any (key=some_key and value=some_value)'
    )

If the query was written without ``any``, projects with one metadata matching 
*key* and another matching the *value* would be returned.

``any`` can also be used to query for empty relationship collections::

    users_without_timelogs = session.query(
        'User where not timelogs any ()'
    )

.. _querying/criteria/operators:

Supported operators
-------------------

This is the list of currently supported operators:

+--------------+----------------+----------------------------------------------+
| Operators    | Description    | Example                                      |
+==============+================+==============================================+
| =            | Exactly equal. | name is "martin"                             |
| is           |                |                                              |
+--------------+----------------+----------------------------------------------+
| !=           | Not exactly    | name is_not "martin"                         |
| is_not       | equal.         |                                              |
+--------------+----------------+----------------------------------------------+
| >            | Greater than   | start after "2015-06-01"                     |
| after        | exclusive.     |                                              |
| greater_than |                |                                              |
+--------------+----------------+----------------------------------------------+
| <            | Less than      | end before "2015-06-01"                      |
| before       | exclusive.     |                                              |
| less_than    |                |                                              |
+--------------+----------------+----------------------------------------------+
| >=           | Greater than   | bid >= 10                                    |
|              | inclusive.     |                                              |
+--------------+----------------+----------------------------------------------+
| <=           | Less than      | bid <= 10                                    |
|              | inclusive.     |                                              |
+--------------+----------------+----------------------------------------------+
| in           | One of.        | status.type.name in ("In Progress", "Done")  |
+--------------+----------------+----------------------------------------------+
| not_in       | Not one of.    | status.name not_in ("Omitted", "On Hold")    |
+--------------+----------------+----------------------------------------------+
| like         | Matches        | name like "%thrones"                         |
|              | pattern.       |                                              |
+--------------+----------------+----------------------------------------------+
| not_like     | Does not match | name not_like "%thrones"                     |
|              | pattern.       |                                              |
+--------------+----------------+----------------------------------------------+
| has          | Test scalar    | author has (first_name is "Jane" and         |
|              | relationship.  | last_name is "Doe")                          |
+--------------+----------------+----------------------------------------------+
| any          | Test collection| metadata any (key=some_key and               |
|              | relationship.  | value=some_value)                            |
+--------------+----------------+----------------------------------------------+

.. _querying/projections:

Optimising using projections
============================

In :ref:`understanding_sessions` we mentioned :ref:`auto-population
<understanding_sessions/auto_population>` of attribute values on access. This
meant that when iterating over a lot of entities and attributes a large number
of queries were being sent to the server. Ultimately, this can cause your code
to run slowly::

    >>> projects = session.query('Project')
    >>> for project in projects:
    ...     print(
    ...         # Multiple queries issued here for each attribute accessed for
    ...         # each project in the loop!
    ...         '{project[full_name]} - {project[status][name]})'
    ...         .format(project=project)
    ...     )


Fortunately, there is an easy way to optimise. If you know what attributes you
are interested in ahead of time you can include them in your query string as
*projections* in order to fetch them in one go::

    >>> projects = session.query(
    ...     'select full_name, status.name from Project'
    ... )
    >>> for project in projects:
    ...     print(
    ...         # No additional queries issued here as the values were already
    ...         # loaded by the above query!
    ...         '{project[full_name]} - {project[status][name]})'
    ...         .format(project=project)
    ...     )

Notice how this works for related entities as well. In the example above, we
also fetched the name of each *Status* entity attached to a project in the same
query, which meant that no further queries had to be issued when accessing those
nested attributes.

.. note::

    There are no arbitrary limits to the number (or depth) of projections, but
    do be aware that excessive projections can ultimately result in poor
    performance also. As always, it is about choosing the right tool for the
    job.

You can also customise the
:ref:`working_with_entities/entity_types/default_projections` to use for each
entity type when none are specified in the query string.
