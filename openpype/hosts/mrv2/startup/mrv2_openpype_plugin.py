import contextlib
import sys

from mrv2 import plugin, cmd

from openpype.pipeline import install_host
from openpype.hosts.mrv2.api import Mrv2Host


def separator():
    # Do nothing function, temporary until mrv2 exposes separator functionality
    pass


class MyPlugin(plugin.Plugin):
    def on_create(self):
        from openpype.tools.utils import host_tools
        with qt_app():
            host_tools.show_publisher(tab="create")

    def on_load(self):
        from openpype.tools.utils import host_tools
        with qt_app():
            host_tools.show_loader(use_context=True)

    def on_publish(self):
        from openpype.tools.utils import host_tools
        with qt_app():
            host_tools.show_publisher(tab="publish")

    def on_manage(self):
        from openpype.tools.utils import host_tools
        with qt_app():
            host_tools.show_scene_inventory()

    def on_library(self):
        from openpype.tools.utils import host_tools
        with qt_app():
            host_tools.show_library_loader()

    def on_workfiles(self):
        from openpype.tools.utils import host_tools
        with qt_app():
            host_tools.show_workfiles()

    def menus(self):
        top = "OpenPype"
        return {
            f"{top}/Create...": self.on_create,
            f"{top}/Load...": self.on_load,
            f"{top}/Publish...": self.on_publish,
            f"{top}/Manage...": self.on_manage,
            f"{top}/Library...": self.on_library,
            f"{top}/-------": separator,
            f"{top}/Workfiles...": self.on_workfiles,
        }


@contextlib.contextmanager
def qt_app():
    """Create QApplication instance without calling `exec_()`

    Somehow the Qt UI updates fine within MRV2 without calling exec.
    It even performs better because it doesnt crash MRV2, see:
        https://github.com/ggarra13/mrv2/issues/130

    """
    from qtpy import QtWidgets
    app = QtWidgets.QApplication.instance()
    if not app:
        print("Creating QApplication instance")
        app = QtWidgets.QApplication(sys.argv)

    yield app


def install():
    print("Installing OpenPype..")
    host = Mrv2Host()
    install_host(host)


install()
