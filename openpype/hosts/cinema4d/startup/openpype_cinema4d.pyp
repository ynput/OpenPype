import os
import sys
# C4D doesn't ship with python3.dll which PySide is
# built against. 
# 
# Python3.8+ uses os.add_dll_directory to load dlls
# Previous version just add to the path
if "win" in sys.platform:
    dll_dirs = os.getenv("OPENPYPE_DLL_DIRS") or ""

    for path in dll_dirs.split(os.pathsep):
        if not path:
            continue
        try:
            norm_path = os.path.normpath(path)
            os.add_dll_directory(path)
        except AttributeError:
            os.environ["PATH"] = norm_path + os.pathsep + os.environ["PATH"]

import c4d


from openpype.pipeline import install_host
from openpype.hosts.cinema4d.api import Cinema4DHost
from openpype.hosts.cinema4d.api.lib import get_main_window
from openpype.hosts.cinema4d.api import lib
from openpype.hosts.cinema4d.api.commands import reset_frame_range
from openpype.api import BuildWorkfile
from openpype.settings import get_current_project_settings
from openpype.pipeline import legacy_io
from openpype.tools.utils import host_tools



loader_id = 1059864
creator_id = 1059865
publish_id = 1059866
scene_inventory_id = 1059867
library_id = 1059868
workfiles_id = 1059869
build_workfile_id = 1059873
reset_frame_range_id = 1059870
reset_scene_resolution_id = 1059871
reset_colorspace_id = 1059874
experimental_tools_id = 1059872

class Loader(c4d.plugins.CommandData):
    def Execute(self, doc):
        host_tools.show_loader(
            parent=get_main_window(),
            use_context=True
        )
        return True

class Creator(c4d.plugins.CommandData):
    def Execute(self, doc):
        host_tools.show_creator(
            parent=get_main_window()
        )
        return True

class Publish(c4d.plugins.CommandData):
    def Execute(self, doc):
        host_tools.show_publish(
            parent=get_main_window()
        )
        return True

class SceneInventory(c4d.plugins.CommandData):
    def Execute(self, doc):
        host_tools.show_scene_inventory(
            parent=get_main_window()
        )
        return True

class Library(c4d.plugins.CommandData):
    def Execute(self, doc):
        host_tools.show_library_loader(
            parent=get_main_window()
        )
        return True

class Workfiles(c4d.plugins.CommandData):
    def Execute(self, doc):
        host_tools.show_workfiles(
            parent=get_main_window()
        )
        return True

class BuildWorkFile(c4d.plugins.CommandData):
    def Execute(self, doc):
        BuildWorkFile().process()
        return True

class ResetFrameRange(c4d.plugins.CommandData):
    def Execute(self, doc):
        return True

class ResetSceneResolution(c4d.plugins.CommandData):
    def Execute(self, doc):
        return True

class ResetColorspace(c4d.plugins.CommandData):
    def Execute(self, doc):
        return True

class ExperimentalTools(c4d.plugins.CommandData):
    def Execute(self, doc):
        host_tools.show_experimental_tools_dialog(
            get_main_window()
        )
        return True


def EnhanceMainMenu():
    mainMenu = c4d.gui.GetMenuResource("M_EDITOR")
    pluginsMenu = c4d.gui.SearchPluginMenuResource()

    menu = c4d.BaseContainer()

    menu.InsData(c4d.MENURESOURCE_SUBTITLE, legacy_io.Session["AVALON_LABEL"])
    menu.InsData(c4d.MENURESOURCE_COMMAND, "PLUGIN_CMD_1059864")
    menu.InsData(c4d.MENURESOURCE_COMMAND, "PLUGIN_CMD_1059865")
    menu.InsData(c4d.MENURESOURCE_COMMAND, "PLUGIN_CMD_1059866")
    menu.InsData(c4d.MENURESOURCE_COMMAND, "PLUGIN_CMD_1059867")
    menu.InsData(c4d.MENURESOURCE_COMMAND, "PLUGIN_CMD_1059868")
    menu.InsData(c4d.MENURESOURCE_COMMAND, "PLUGIN_CMD_1059869")
    menu.InsData(c4d.MENURESOURCE_COMMAND, "PLUGIN_CMD_1059873")
    menu.InsData(c4d.MENURESOURCE_COMMAND, "PLUGIN_CMD_1059870")
    menu.InsData(c4d.MENURESOURCE_COMMAND, "PLUGIN_CMD_1059871")
    menu.InsData(c4d.MENURESOURCE_COMMAND, "PLUGIN_CMD_1059874")
    menu.InsData(c4d.MENURESOURCE_COMMAND, "PLUGIN_CMD_1059872")

    if pluginsMenu:
        mainMenu.InsDataAfter(c4d.MENURESOURCE_STRING, menu, pluginsMenu)
    else:
        mainMenu.InsData(c4d.MENURESOURCE_STRING, menu)

def PluginMessage(id, data):
    if id==c4d.C4DPL_BUILDMENU:
        EnhanceMainMenu()


if __name__ == '__main__':

    host = Cinema4DHost()
    install_host(host)

    c4d.plugins.RegisterCommandPlugin(loader_id, "Loader", 0, None, "", Loader())
    c4d.plugins.RegisterCommandPlugin(creator_id, "Creator", 0, None, "", Creator())
    c4d.plugins.RegisterCommandPlugin(publish_id, "Publish", 0, None, "", Publish())
    c4d.plugins.RegisterCommandPlugin(scene_inventory_id, "Inventory", 0, None, "", SceneInventory())
    c4d.plugins.RegisterCommandPlugin(library_id, "Library", 0, None, "", Library())
    c4d.plugins.RegisterCommandPlugin(workfiles_id, "Workfiles", 0, None, "", Workfiles())
    c4d.plugins.RegisterCommandPlugin(build_workfile_id, "Build Workfile", 0, None, "", BuildWorkFile())
    c4d.plugins.RegisterCommandPlugin(reset_frame_range_id, "Reset Frame Range", 0, None, "", ResetFrameRange())
    c4d.plugins.RegisterCommandPlugin(
        reset_scene_resolution_id, "Reset Scene Resolution", 0, None, "", ResetSceneResolution())
    c4d.plugins.RegisterCommandPlugin(reset_colorspace_id, "Reset Colorspace", 0, None, "", ResetColorspace())
    c4d.plugins.RegisterCommandPlugin(
        experimental_tools_id, "Experimental Tools", 0, None, "", ExperimentalTools())
