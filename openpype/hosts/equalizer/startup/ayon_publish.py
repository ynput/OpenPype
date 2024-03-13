#
# 3DE4.script.name:     Publish ...
# 3DE4.script.gui:      Main Window::Ayon
# 3DE4.script.comment:  Open AYON Publisher tool
#

from openpype.pipeline import install_host, is_installed
from openpype.hosts.equalizer.api import EqualizerHost
from openpype.tools.utils import host_tools


def install_3de_host():
    print("Running AYON integration ...")
    install_host(EqualizerHost())


if not is_installed():
    install_3de_host()

# show the UI
print("Opening publisher window ...")
host_tools.show_publisher(
    tab="publish", parent=EqualizerHost.get_host().get_main_window())
