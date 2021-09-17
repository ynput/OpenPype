import sys
from Qt import QtWidgets, QtCore
from pprint import pprint, pformat
import time
import atexit
import openpype.hosts.flame as opflame

# Exception handler
def exeption_handler(exctype, value, tb):
    import traceback
    msg = "OpenPype: Python exception {} in {}".format(value, exctype)
    mbox = QtWidgets.QMessageBox()
    mbox.setText(msg)
    mbox.setDetailedText(pformat(traceback.format_exception(exctype, value, tb)))
    mbox.setStyleSheet('QLabel{min-width: 800px;}')
    mbox.exec_()
    sys.__excepthook__(exctype, value, tb)


# add exception handler into sys module
sys.excepthook = exeption_handler


# register clean up logic to be called at Flame exit
def cleanup():
    if opflame.apps:
        print('[DEBUG %s] unloading apps:\n%s' % ('flameMenuSG', pformat(opflame.apps)))
        while len(opflame.apps):
            app = opflame.apps.pop()
            print('[DEBUG %s] unloading: %s' % ('flameMenuSG', app.name))
            del app
        opflame.apps = []

    if opflame.app_framework:
        print ('PYTHON\t: %s cleaning up' % opflame.app_framework.bundle_name)
        opflame.app_framework.save_prefs()
        opflame.app_framework = None

atexit.register(cleanup, opflame.apps, opflame.app_framework)

def load_apps():
    opflame.apps.append(opflame.FlameMenuProjectconnect(opflame.app_framework))
    opflame.app_framework.log.info("Apps are loaded")

def rescan_hooks():
    try:
        import flame
        flame.execute_shortcut('Rescan Python Hooks')
    except:
        pass

def project_changed_dict(info):
    cleanup()

def app_initialized(project_name):
    opflame.app_framework = opflame.FlameAppFramework()
    print ('PYTHON\t: %s initializing' % opflame.app_framework.bundle_name)
    print("*" * 100)
    print(project_name)
    print("*" * 100)
    load_apps()

try:
    import flame
    app_initialized(flame.project.current_project.name)
except:
    pass

def project_saved(project_name, save_time, is_auto_save):
    if opflame.app_framework:
        opflame.app_framework.save_prefs()


def get_main_menu_custom_ui_actions():
    start = time.time()
    menu = []
    flameMenuProjectconnectApp = None
    for app in opflame.apps:
        if app.__class__.__name__ == 'flameMenuProjectconnect':
            flameMenuProjectconnectApp = app
    if flameMenuProjectconnectApp:
        menu.append(flameMenuProjectconnectApp.build_menu())
    if menu:
        menu[0]['actions'].append({'name': "openpype_version_3", 'isEnabled': False})

    if opflame.app_framework:
        menu_auto_refresh = opflame.app_framework.prefs_global.get(
            'menu_auto_refresh', {})
        if menu_auto_refresh.get('main_menu', True):
            try:
                import flame
                flame.schedule_idle_event(rescan_hooks)
            except:
                pass

    print('main menu update took %s' % (time.time() - start))

    return menu
