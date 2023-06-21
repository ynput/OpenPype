from openpype.pipeline import install_host
from openpype.hosts.nuke.api import NukeHost

host = NukeHost()
install_host(host)

# TODO horent:old heck with output format, see hornet commit 153ccd9
