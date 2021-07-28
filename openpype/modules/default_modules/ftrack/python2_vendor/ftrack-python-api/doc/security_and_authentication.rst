..
    :copyright: Copyright (c) 2014 ftrack

.. _security_and_authentication:

***************************
Security and authentication
***************************

Self signed SSL certificate
===========================

When using a self signed SSL certificate the API may fail to connect if it
cannot verify the SSL certificate. Under the hood the
`requests <http://docs.python-requests.org/en/latest/>`_ library is used and it
must be specified where the trusted certificate authority can be found using the
environment variable ``REQUESTS_CA_BUNDLE``.

.. seealso:: `SSL Cert Verification <http://docs.python-requests.org/en/latest/user/advanced/?highlight=requests_ca_bundle#ssl-cert-verification>`_

InsecurePlatformWarning
=======================

When using this API you may sometimes see a warning::

    InsecurePlatformWarning: A true SSLContext object is not available. This
    prevents urllib3 from configuring SSL appropriately and may cause certain
    SSL connections to fail.

If you encounter this warning, its recommended you upgrade to Python 2.7.9, or
use pyOpenSSL. To use pyOpenSSL simply::

    pip install pyopenssl ndg-httpsclient pyasn1

and the `requests <http://docs.python-requests.org/en/latest/>`_ library used by
this API will use pyOpenSSL instead.

.. seealso:: `InsecurePlatformWarning <http://urllib3.readthedocs.org/en/latest/security.html#insecureplatformwarning>`_
