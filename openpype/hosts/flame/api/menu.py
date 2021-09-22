import os
import sys
from Qt import QtWidgets, QtCore
from pprint import pprint, pformat
from copy import deepcopy

from .lib import rescan_hooks
from openpype.tools.utils.tools_helper import AvalonToolsHelper


menu_group_name = 'OpenPype'

default_flame_export_presets = {
    'Publish': {'PresetVisibility': 2, 'PresetType': 0, 'PresetFile': 'OpenEXR/OpenEXR (16-bit fp PIZ).xml'},
    'Preview': {'PresetVisibility': 3, 'PresetType': 2, 'PresetFile': 'Generate Preview.xml'},
    'Thumbnail': {'PresetVisibility': 3, 'PresetType': 0, 'PresetFile': 'Generate Thumbnail.xml'}
}

class _FlameMenuApp(object):
    def __init__(self, framework):
        self.name = self.__class__.__name__
        self.framework = framework
        self.log = framework.log
        self.menu_group_name = menu_group_name
        self.dynamic_menu_data = {}

        # flame module is only avaliable when a
        # flame project is loaded and initialized
        self.flame = None
        try:
            import flame
            self.flame = flame
        except:
            self.flame = None

        self.flame_project_name = flame.project.current_project.name
        self.prefs = self.framework.prefs_dict(self.framework.prefs, self.name)
        self.prefs_user = self.framework.prefs_dict(
            self.framework.prefs_user, self.name)
        self.prefs_global = self.framework.prefs_dict(
            self.framework.prefs_global, self.name)

        self.mbox = QtWidgets.QMessageBox()

        self.menu = {
            "actions": [{
                'name': os.getenv("AVALON_PROJECT", "project"),
                'isEnabled': False
            }],
            "name": self.menu_group_name
        }
        self.tools_helper = AvalonToolsHelper()

    def __getattr__(self, name):
        def method(*args, **kwargs):
            print('calling %s' % name)
        return method

    def rescan(self, *args, **kwargs):
        if not self.flame:
            try:
                import flame
                self.flame = flame
            except:
                self.flame = None

        if self.flame:
            self.flame.execute_shortcut('Rescan Python Hooks')
            self.log.info('Rescan Python Hooks')


class FlameMenuProjectconnect(_FlameMenuApp):

    # flameMenuProjectconnect app takes care of the preferences dialog as well

    def __init__(self, framework):
        _FlameMenuApp.__init__(self, framework)

    def __getattr__(self, name):
        def method(*args, **kwargs):
            project = self.dynamic_menu_data.get(name)
            if project:
                self.link_project(project)
        return method

    def build_menu(self):
        from avalon.tools import publish

        # todo: load all active projects from db and offer link

        if not self.flame:
            return []

        flame_project_name = self.flame_project_name
        self.log.info("______ {} ______".format(flame_project_name))

        menu = deepcopy(self.menu)

        menu['actions'].append({
            "name": "Workfiles ...",
            "execute": lambda x: self.tools_helper.show_workfiles_tool()
        })
        menu['actions'].append({
            "name": "Create ...",
            "execute": lambda x: self.tools_helper.show_creator_tool()
        })
        menu['actions'].append({
            "name": "Publish ...",
            "execute": lambda x: publish.show()
        })
        menu['actions'].append({
            "name": "Load ...",
            "execute": lambda x: self.tools_helper.show_loader_tool()
        })
        menu['actions'].append({
            "name": "Manage ...",
            "execute": lambda x: self.tools_helper.show_scene_inventory_tool()
        })
        menu['actions'].append({
            "name": "Library ...",
            "execute": lambda x: self.tools_helper.show_library_loader_tool()
        })
        return menu

    def get_projects(self, *args, **kwargs):
        pass

    def refresh(self, *args, **kwargs):
        self.rescan()

    def rescan(self, *args, **kwargs):
        if not self.flame:
            try:
                import flame
                self.flame = flame
            except:
                self.flame = None

        if self.flame:
            self.flame.execute_shortcut('Rescan Python Hooks')
            self.log.info('Rescan Python Hooks')


class FlameMenuTimeline(_FlameMenuApp):

    # flameMenuProjectconnect app takes care of the preferences dialog as well

    def __init__(self, framework):
        _FlameMenuApp.__init__(self, framework)

    def __getattr__(self, name):
        def method(*args, **kwargs):
            project = self.dynamic_menu_data.get(name)
            if project:
                self.link_project(project)
        return method

    def build_menu(self):
        from avalon.tools import publish

        # todo: load all active projects from db and offer link

        if not self.flame:
            return []

        flame_project_name = self.flame_project_name
        self.log.info("______ {} ______".format(flame_project_name))

        menu = deepcopy(self.menu)

        menu['actions'].append({
            "name": "Workfiles ...",
            "execute": lambda x: self.tools_helper.show_workfiles_tool()
        })
        menu['actions'].append({
            "name": "Create ...",
            "execute": lambda x: self.tools_helper.show_creator_tool()
        })
        menu['actions'].append({
            "name": "Publish ...",
            "execute": lambda x: publish.show()
        })
        menu['actions'].append({
            "name": "Load ...",
            "execute": lambda x: self.tools_helper.show_loader_tool()
        })
        menu['actions'].append({
            "name": "Manage ...",
            "execute": lambda x: self.tools_helper.show_scene_inventory_tool()
        })
        menu['actions'].append({
            "name": "Library ...",
            "execute": lambda x: self.tools_helper.show_library_loader_tool()
        })
        return menu

    def get_projects(self, *args, **kwargs):
        pass

    def refresh(self, *args, **kwargs):
        self.rescan()

    def rescan(self, *args, **kwargs):
        if not self.flame:
            try:
                import flame
                self.flame = flame
            except:
                self.flame = None

        if self.flame:
            self.flame.execute_shortcut('Rescan Python Hooks')
            self.log.info('Rescan Python Hooks')

def main_menu_build(apps, framework):
    menu = []
    flameMenuProjectconnectApp = None
    for app in apps:
        if app.__class__.__name__ == 'FlameMenuProjectconnect':
            flameMenuProjectconnectApp = app

    if flameMenuProjectconnectApp:
        menu.append(flameMenuProjectconnectApp.build_menu())

    print(">>_> menu was build: {}".format(pformat(menu)))

    if framework:
        menu_auto_refresh = framework.prefs_global.get(
            'menu_auto_refresh', {})
        if menu_auto_refresh.get('main_menu', True):
            try:
                import flame
                flame.schedule_idle_event(rescan_hooks)
            except ImportError:
                print("!!!! not able to import flame module !!!!")

    return menu
