from __future__ import print_function
import sys
from Qt import QtWidgets
from pprint import pformat
import atexit
import openpype
import avalon
import openpype.hosts.flame as opflame

flh = sys.modules[__name__]
flh._project = None


def openpype_install():
    """Registering OpenPype in context
    """
    openpype.install()
    avalon.api.install(opflame)
    print("Avalon registered hosts: {}".format(
        avalon.api.registered_host()))


# Exception handler
def exeption_handler(exctype, value, _traceback):
    """Exception handler for improving UX

    Args:
        exctype (str): type of exception
        value (str): exception value
        tb (str): traceback to show
    """
    import traceback
    msg = "OpenPype: Python exception {} in {}".format(value, exctype)
    mbox = QtWidgets.QMessageBox()
    mbox.setText(msg)
    mbox.setDetailedText(
        pformat(traceback.format_exception(exctype, value, _traceback)))
    mbox.setStyleSheet('QLabel{min-width: 800px;}')
    mbox.exec_()
    sys.__excepthook__(exctype, value, _traceback)


# add exception handler into sys module
sys.excepthook = exeption_handler


# register clean up logic to be called at Flame exit
def cleanup():
    """Cleaning up Flame framework context
    """
    if opflame.apps:
        print('`{}` cleaning up apps:\n {}\n'.format(
            __file__, pformat(opflame.apps)))
        while len(opflame.apps):
            app = opflame.apps.pop()
            print('`{}` removing : {}'.format(__file__, app.name))
            del app
        opflame.apps = []

    if opflame.app_framework:
        print('PYTHON\t: %s cleaning up' % opflame.app_framework.bundle_name)
        opflame.app_framework.save_prefs()
        opflame.app_framework = None


atexit.register(cleanup)


def load_apps():
    """Load available apps into Flame framework
    """
    opflame.apps.append(opflame.FlameMenuProjectConnect(opflame.app_framework))
    opflame.apps.append(opflame.FlameMenuTimeline(opflame.app_framework))
    opflame.app_framework.log.info("Apps are loaded")


def project_changed_dict(info):
    """Hook for project change action

    Args:
        info (str): info text
    """
    cleanup()


def app_initialized(parent=None):
    """Inicialization of Framework

    Args:
        parent (obj, optional): Parent object. Defaults to None.
    """
    opflame.app_framework = opflame.FlameAppFramework()

    print("{} initializing".format(
        opflame.app_framework.bundle_name))

    load_apps()


"""
Initialisation of the hook is starting from here

First it needs to test if it can import the flame module.
This will happen only in case a project has been loaded.
Then `app_initialized` will load main Framework which will load
all menu objects as apps.
"""

try:
    import flame  # noqa
    app_initialized(parent=None)
except ImportError:
    print("!!!! not able to import flame module !!!!")


def rescan_hooks():
    import flame  # noqa
    flame.execute_shortcut('Rescan Python Hooks')


def _build_app_menu(app_name):
    """Flame menu object generator

    Args:
        app_name (str): name of menu object app

    Returns:
        list: menu object
    """
    menu = []

    # first find the relative appname
    app = None
    for _app in opflame.apps:
        if _app.__class__.__name__ == app_name:
            app = _app

    if app:
        menu.append(app.build_menu())

    if opflame.app_framework:
        menu_auto_refresh = opflame.app_framework.prefs_global.get(
            'menu_auto_refresh', {})
        if menu_auto_refresh.get('timeline_menu', True):
            try:
                import flame  # noqa
                flame.schedule_idle_event(rescan_hooks)
            except ImportError:
                print("!-!!! not able to import flame module !!!!")

    return menu


""" Flame hooks are starting here
"""


def project_saved(project_name, save_time, is_auto_save):
    """Hook to activate when project is saved

    Args:
        project_name (str): name of project
        save_time (str): time when it was saved
        is_auto_save (bool): autosave is on or off
    """
    if opflame.app_framework:
        opflame.app_framework.save_prefs()


def get_main_menu_custom_ui_actions():
    """Hook to create submenu in start menu

    Returns:
        list: menu object
    """
    # install openpype and the host
    openpype_install()

    return _build_app_menu("FlameMenuProjectConnect")


def get_timeline_custom_ui_actions():
    """Hook to create submenu in timeline

    Returns:
        list: menu object
    """
    # install openpype and the host
    openpype_install()

    return _build_app_menu("FlameMenuTimeline")
