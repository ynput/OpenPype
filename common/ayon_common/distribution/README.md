Addon distribution tool
------------------------

Code in this folder is backend portion of Addon distribution logic for v4 server.

Each host, module will be separate Addon in the future. Each v4 server could run different set of Addons.

Client (running on artist machine) will in the first step ask v4 for list of enabled addons.
(It expects list of json documents matching to `addon_distribution.py:AddonInfo` object.)
Next it will compare presence of enabled addon version in local folder. In the case of missing version of
an addon, client will use information in the addon to download (from http/shared local disk/git) zip file
and unzip it.

Required part of addon distribution will be sharing of dependencies (python libraries, utilities) which is not part of this folder.

Location of this folder might change in the future as it will be required for a clint to add this folder to sys.path reliably.

This code needs to be independent on Openpype code as much as possible!
