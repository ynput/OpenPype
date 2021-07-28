..
    :copyright: Copyright (c) 2014 ftrack

.. _installing:

**********
Installing
**********

.. highlight:: bash

Installation is simple with `pip <http://www.pip-installer.org/>`_::

    pip install ftrack-python-api

Building from source
====================

You can also build manually from the source for more control. First obtain a
copy of the source by either downloading the
`zipball <https://bitbucket.org/ftrack/ftrack-python-api/get/master.zip>`_ or
cloning the public repository::

    git clone git@bitbucket.org:ftrack/ftrack-python-api.git

Then you can build and install the package into your current Python
site-packages folder::

    python setup.py install

Alternatively, just build locally and manage yourself::

    python setup.py build

Building documentation from source
----------------------------------

To build the documentation from source::

    python setup.py build_sphinx

Then view in your browser::

    file:///path/to/ftrack-python-api/build/doc/html/index.html

Running tests against the source
--------------------------------

With a copy of the source it is also possible to run the unit tests::

    python setup.py test

Dependencies
============

* `ftrack server <http://ftrack.rtd.ftrack.com/en/stable/>`_ >= 3.3.11
* `Python <http://python.org>`_ >= 2.7, < 3
* `Requests <http://docs.python-requests.org>`_ >= 2, <3,
* `Arrow <http://crsmithdev.com/arrow/>`_ >= 0.4.4, < 1,
* `termcolor <https://pypi.python.org/pypi/termcolor>`_ >= 1.1.0, < 2,
* `pyparsing <http://pyparsing.wikispaces.com/>`_ >= 2.0, < 3,
* `Clique <http://clique.readthedocs.org/>`_ >= 1.2.0, < 2,
* `websocket-client <https://pypi.python.org/pypi/websocket-client>`_ >= 0.40.0, < 1

Additional For building
-----------------------

* `Sphinx <http://sphinx-doc.org/>`_ >= 1.2.2, < 2
* `sphinx_rtd_theme <https://github.com/snide/sphinx_rtd_theme>`_ >= 0.1.6, < 1
* `Lowdown <http://lowdown.rtd.ftrack.com/en/stable/>`_ >= 0.1.0, < 2

Additional For testing
----------------------

* `Pytest <http://pytest.org>`_  >= 2.3.5, < 3
* `pytest-mock <https://pypi.python.org/pypi/pytest-mock/>`_ >= 0.4, < 1,
* `pytest-catchlog <https://pypi.python.org/pypi/pytest-catchlog/>`_ >= 1, <=2