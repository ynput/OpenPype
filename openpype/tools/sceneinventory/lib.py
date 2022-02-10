import os
from openpype_modules import sync_server

from Qt import QtGui


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


def get_progress_for_repre(repre_doc, active_site, remote_site):
    """
        Calculates average progress for representation.

        If site has created_dt >> fully available >> progress == 1

        Could be calculated in aggregate if it would be too slow
        Args:
            repre_doc(dict): representation dict
        Returns:
            (dict) with active and remote sites progress
            {'studio': 1.0, 'gdrive': -1} - gdrive site is not present
                -1 is used to highlight the site should be added
            {'studio': 1.0, 'gdrive': 0.0} - gdrive site is present, not
                uploaded yet
    """
    progress = {active_site: -1, remote_site: -1}
    if not repre_doc:
        return progress

    files = {active_site: 0, remote_site: 0}
    doc_files = repre_doc.get("files") or []
    for doc_file in doc_files:
        if not isinstance(doc_file, dict):
            continue

        sites = doc_file.get("sites") or []
        for site in sites:
            if (
                # Pype 2 compatibility
                not isinstance(site, dict)
                # Check if site name is one of progress sites
                or site["name"] not in progress
            ):
                continue

            files[site["name"]] += 1
            norm_progress = max(progress[site["name"]], 0)
            if site.get("created_dt"):
                progress[site["name"]] = norm_progress + 1
            elif site.get("progress"):
                progress[site["name"]] = norm_progress + site["progress"]
            else:  # site exists, might be failed, do not add again
                progress[site["name"]] = 0

    # for example 13 fully avail. files out of 26 >> 13/26 = 0.5
    avg_progress = {
        active_site: progress[active_site] / max(files[active_site], 1),
        remote_site: progress[remote_site] / max(files[remote_site], 1)
    }
    return avg_progress
