..
    :copyright: Copyright (c) 2015 ftrack

.. _example/custom_attribute:

***********************
Using custom attributes
***********************

.. currentmodule:: ftrack_api.session

Custom attributes can be written and read from entities using the
``custom_attributes`` property.

The ``custom_attributes`` property provides a similar interface to a dictionary.

Keys can be printed using the keys method::

    >>> task['custom_attributes'].keys()
    [u'my_text_field']

or access keys and values as items::

    >>> print task['custom_attributes'].items()
    [(u'my_text_field', u'some text')]

Read existing custom attribute values::

    >>> print task['custom_attributes']['my_text_field']
    'some text'

Updating a custom attributes can also be done similar to a dictionary::

    task['custom_attributes']['my_text_field'] = 'foo'

To query for tasks with a custom attribute, ``my_text_field``, you can use the
key from the configuration::
 
    for task in session.query(
        'Task where custom_attributes any '
        '(key is "my_text_field" and value is "bar")'
    ):
        print task['name']

Limitations
===========

Expression attributes
---------------------

Expression attributes are not yet supported and the reported value will
always be the non-evaluated expression.

Hierarchical attributes
-----------------------

Hierarchical attributes are not yet fully supported in the API. Hierarchical
attributes support both read and write, but when read they are not calculated
and instead the `raw` value is returned::

    # The hierarchical attribute `my_attribute` is set on Shot but this will not
    # be reflected on the children. Instead the raw value is returned.
    print shot['custom_attributes']['my_attribute']
    'foo'
    print task['custom_attributes']['my_attribute']
    None

To work around this limitation it is possible to use the legacy api for
hierarchical attributes or to manually query the parents for values and use the
first value that is set.

Validation
==========

Custom attributes are validated on the ftrack server before persisted. The
validation will check that the type of the data is correct for the custom
attribute.

    * number - :py:class:`int` or :py:class:`float`
    * text - :py:class:`str` or :py:class:`unicode`
    * enumerator - :py:class:`list`
    * boolean - :py:class:`bool`
    * date - :py:class:`datetime.datetime` or :py:class:`datetime.date`

If the value set is not valid a :py:exc:`ftrack_api.exception.ServerError` is
raised with debug information::

    shot['custom_attributes']['fstart'] = 'test'

    Traceback (most recent call last):
        ...
    ftrack_api.exception.ServerError: Server reported error: 
    ValidationError(Custom attribute value for "fstart" must be of type number.
    Got "test" of type <type 'unicode'>)