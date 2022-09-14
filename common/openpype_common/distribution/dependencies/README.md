Addon dependencies distribution tool
------------------------------------

Code in this folder is backend portion of Addon distribution of dependencies for v4 server.

This should collect info about all enabled addons on the v4 server, reads its
pyproject.tomls, create one merged one (it tries to find common denominator for dependency version).

Then it uses Poetry to create new venv, zips it and provides this to v4 server for distribution to 
all clients.

It is expected to be run on machine that has set reasonable development environment (cmake probably).

Should be standalone, not depending on Openpype libraries.