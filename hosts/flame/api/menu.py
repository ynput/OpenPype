import os
from Qt import QtWidgets
from copy import deepcopy
from pprint import pformat
from openpype.tools.utils.host_tools import HostToolsHelper

menu_group_name = 'OpenPype'

default_flame_export_presets = {
    'Publish': {
        'PresetVisibility': 2,
        'PresetType': 0,
        'PresetFile': 'OpenEXR/OpenEXR (16-bit fp PIZ).xml'
    },
    'Preview': {
        'PresetVisibility': 3,
        'PresetType': 2,
        'PresetFile': 'Generate Preview.xml'
    },
    'Thumbnail': {
        'PresetVisibility': 3,
        'PresetType': 0,
        'PresetFile': 'Generate Thumbnail.xml'
    }
}


def callback_selection(selection, function):
    import openpype.hosts.flame.api as opfapi
    opfapi.CTX.selection = selection
    print("Hook Selection: \n\t{}".format(
        pformat({
            index: (type(item), item.name)
            for index, item in enumerate(opfapi.CTX.selection)})
    ))
    function()


class _FlameMenuApp(object):
    def __init__(self, framework):
        self.name = self.__class__.__name__
        self.framework = framework
        self.log = framework.log
        self.menu_group_name = menu_group_name
        self.dynamic_menu_data = {}

        # flame module is only available when a
        # flame project is loaded and initialized
        self.flame = None
        try:
            import flame
            self.flame = flame
        except ImportError:
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
        self.tools_helper = HostToolsHelper()

    def __getattr__(self, name):
        def method(*args, **kwargs):
            print('calling %s' % name)
        return method

    def rescan(self, *args, **kwargs):
        if not self.flame:
            try:
                import flame
                self.flame = flame
            except ImportError:
                self.flame = None

        if self.flame:
            self.flame.execute_shortcut('Rescan Python Hooks')
            self.log.info('Rescan Python Hooks')


class FlameMenuProjectConnect(_FlameMenuApp):

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
        if not self.flame:
            return []

        menu = deepcopy(self.menu)

        menu['actions'].append({
            "name": "Workfiles...",
            "execute": lambda x: self.tools_helper.show_workfiles()
        })
        menu['actions'].append({
            "name": "Load...",
            "execute": lambda x: self.tools_helper.show_loader()
        })
        menu['actions'].append({
            "name": "Manage...",
            "execute": lambda x: self.tools_helper.show_scene_inventory()
        })
        menu['actions'].append({
            "name": "Library...",
            "execute": lambda x: self.tools_helper.show_library_loader()
        })
        return menu

    def refresh(self, *args, **kwargs):
        self.rescan()

    def rescan(self, *args, **kwargs):
        if not self.flame:
            try:
                import flame
                self.flame = flame
            except ImportError:
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
        if not self.flame:
            return []

        menu = deepcopy(self.menu)

        menu['actions'].append({
            "name": "Create...",
            "execute": lambda x: callback_selection(
                x, self.tools_helper.show_creator)
        })
        menu['actions'].append({
            "name": "Publish...",
            "execute": lambda x: callback_selection(
                x, self.tools_helper.show_publish)
        })
        menu['actions'].append({
            "name": "Load...",
            "execute": lambda x: self.tools_helper.show_loader()
        })
        menu['actions'].append({
            "name": "Manage...",
            "execute": lambda x: self.tools_helper.show_scene_inventory()
        })
        menu['actions'].append({
            "name": "Library...",
            "execute": lambda x: self.tools_helper.show_library_loader()
        })
        return menu

    def refresh(self, *args, **kwargs):
        self.rescan()

    def rescan(self, *args, **kwargs):
        if not self.flame:
            try:
                import flame
                self.flame = flame
            except ImportError:
                self.flame = None

        if self.flame:
            self.flame.execute_shortcut('Rescan Python Hooks')
            self.log.info('Rescan Python Hooks')
