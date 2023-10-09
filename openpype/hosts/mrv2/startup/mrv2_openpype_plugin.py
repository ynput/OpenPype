from mrv2 import plugin


def separator():
    # Do nothing function, temporary until mrv2 exposes separator functionality
    pass


class MyPlugin(plugin.Plugin):
    def on_create(self):
        print("Create..")
        from openpype.tools.utils import host_tools
        host_tools.show_publisher(tab="create")

    def on_load(self):
        print("Load..")
        from openpype.tools.utils import host_tools
        host_tools.show_loader(use_context=True)

    def on_publish(self):
        print("Publish..")
        from openpype.tools.utils import host_tools
        host_tools.show_publisher(tab="publish")

    def on_manage(self):
        print("Manage..")
        from openpype.tools.utils import host_tools
        host_tools.show_scene_inventory()

    def on_library(self):
        print("Library..")
        from openpype.tools.utils import host_tools
        host_tools.show_library_loader()

    def on_workfiles(self):
        print("Workfiles..")
        from openpype.tools.utils import host_tools
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


def install():
    from openpype.pipeline import install_host
    from openpype.hosts.mrv2.api import Mrv2Host
    print("Installing OpenPype..")
    host = Mrv2Host()
    install_host(host)


install()
