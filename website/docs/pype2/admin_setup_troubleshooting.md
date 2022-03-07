---
id: admin_setup_troubleshooting
title: Setup Troubleshooting
sidebar_label: Setup Troubleshooting
---

## SSL Server certificates

Python is strict about certificates when connecting to server with SSL. If
certificate cannot be validated, connection will fail. Therefore care must be
taken when using self-signed certificates to add their certification authority
to trusted certificates.

Also please note that even when using certificates from trusted CA, you need to
update your trusted CA certificates bundle as those certificates can change.

So if you receive SSL error `cannot validate certificate` or similar, please update root CA certificate bundle on machines and possibly **certifi** python package in Pype virtual environment - just edit `pypeapp/requirements.txt` and update its version. You can find current versions on [PyPI](https://pypi.org).
