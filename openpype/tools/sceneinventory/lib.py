import os
from openpype_modules import sync_server

from qtpy import QtGui


def walk_hierarchy(node):
    """Recursively yield group node."""
    for child in node.children():
        if child.get("isGroupNode"):
            yield child

        for _child in walk_hierarchy(child):
            yield _child


def get_site_icons():
    resource_path = os.path.join(
        os.path.dirname(sync_server.sync_server_module.__file__),
        "providers",
        "resources"
    )
    icons = {}
    # TODO get from sync module
    for provider in ["studio", "local_drive", "gdrive"]:
        pix_url = "{}/{}.png".format(resource_path, provider)
        icons[provider] = QtGui.QIcon(pix_url)

    return icons

