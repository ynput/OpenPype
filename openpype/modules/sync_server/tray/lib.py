from Qt import QtWidgets, QtCore, QtGui
from Qt.QtCore import Qt

from openpype.lib import PypeLogger
from openpype.tools.settings import style


log = PypeLogger().get_logger("SyncServer")

STATUS = {
    0: 'In Progress',
    1: 'Queued',
    2: 'Failed',
    3: 'Paused',
    4: 'Synced OK',
    -1: 'Not available'
}

DUMMY_PROJECT = "No project configured"

ProviderRole = QtCore.Qt.UserRole + 2
ProgressRole = QtCore.Qt.UserRole + 4
DateRole = QtCore.Qt.UserRole + 6
FailedRole = QtCore.Qt.UserRole + 8


def pretty_size(value, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(value) < 1024.0:
            return "%3.1f%s%s" % (value, unit, suffix)
        value /= 1024.0
    return "%.1f%s%s" % (value, 'Yi', suffix)


def convert_progress(value):
    try:
        progress = float(value)
    except (ValueError, TypeError):
        progress = 0.0

    return progress


def translate_provider_for_icon(sync_server, project, site):
    """
        Get provider for 'site'

        This is used for getting icon, 'studio' should have different icon
        then local sites, even the provider 'local_drive' is same

    """
    if site == sync_server.DEFAULT_SITE:
        return sync_server.DEFAULT_SITE
    return sync_server.get_provider_for_site(project, site)
