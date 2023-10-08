from mrv2 import plugin
# TODO: We must first distribute Qt to MRV2's Python 3.10
# from openpype.tools.utils import host_tools


def separator():
    pass


class MyPlugin(plugin.Plugin):
    # Should be made available on MRV_PLUGIN_PATH
    # See: https://github.com/ggarra13/mrv2/issues/68
    def on_create(self):
        print("Create..")

    def on_load(self):
        print("Load..")

    def on_publish(self):
        print("Manage..")

    def on_manage(self):
        print("Manage..")

    def on_library(self):
        print("Library..")

    def on_workfiles(self):
        print("Workfiles..")
        # host_tools.show_workfiles()

    def menus(self):
        top = "OpenPype"
        return {
            f"{top}/Create...": self.on_create,
            f"{top}/Load...": self.on_load,
            f"{top}/Publish...": self.on_publish,
            f"{top}/Manage...": self.on_manage,
            f"{top}/Library...": self.on_library,
            f"{top}/": separator,
            f"{top}/Workfiles...": self.on_workfiles,
        }
