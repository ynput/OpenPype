..
    :copyright: Copyright (c) 2014 ftrack

.. _introduction:

************
Introduction
************

This API allows developers to write :term:`Python` scripts that talk directly
with an ftrack server. The scripts can perform operations against that server
depending on granted permissions.

With any API it is important to find the right balance between flexibility and
usefulness. If an API is too low level then everyone ends up writing boilerplate
code for common problems and usually in an non-uniform way making it harder to
share scripts with others. It's also harder to get started with such an API.
Conversely, an API that attempts to be too smart can often become restrictive
when trying to do more advanced functionality or optimise for performance.

With this API we have tried to strike the right balance between these two,
providing an API that should be simple to use out-of-the-box, but also expose
more flexibility and power when needed.

Nothing is perfect though, so please do provide feedback on ways that we can
continue to improve this API for your specific needs.
