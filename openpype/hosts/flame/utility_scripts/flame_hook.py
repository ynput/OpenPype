import sys
from Qt import QtWidgets, QtCore
from pprint import pprint, pformat
import atexit

app_framework = None
apps = []

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
def cleanup(apps, app_framework):
    if apps:
        if DEBUG:
            print ('[DEBUG %s] unloading apps:\n%s' % ('flameMenuSG', pformat(apps)))
        while len(apps):
            app = apps.pop()
            if DEBUG:
                print ('[DEBUG %s] unloading: %s' % ('flameMenuSG', app.name))
            del app
        del apps

    if app_framework:
        print ('PYTHON\t: %s cleaning up' % app_framework.bundle_name)
        app_framework.save_prefs()
        del app_framework

atexit.register(cleanup, apps, app_framework)

def load_apps(apps, app_framework):
    apps.append(flameMenuProjectconnect(app_framework))
    app_framework.apps = apps
    if DEBUG:
        print ('[DEBUG %s] loaded:\n%s' % (app_framework.bundle_name, pformat(apps)))

def rescan_hooks():
    try:
        import flame
        flame.execute_shortcut('Rescan Python Hooks')
    except:
        pass

def project_changed_dict(info):
    global app_framework
    global apps
    cleanup(apps, app_framework)

def app_initialized(project_name):
    global app_framework
    global apps
    app_framework = flameAppFramework()
    print ('PYTHON\t: %s initializing' % app_framework.bundle_name)
    load_apps(apps, app_framework)

try:
    import flame
    app_initialized(flame.project.current_project.name)
except:
    pass

def project_saved(project_name, save_time, is_auto_save):
    global app_framework

    if app_framework:
        app_framework.save_prefs()


def get_main_menu_custom_ui_actions():
    start = time.time()
    menu = []
    flameMenuProjectconnectApp = None
    for app in apps:
        if app.__class__.__name__ == 'flameMenuProjectconnect':
            flameMenuProjectconnectApp = app
    if flameMenuProjectconnectApp:
        menu.append(flameMenuProjectconnectApp.build_menu())
    if menu:
        menu[0]['actions'].append({'name': __version__, 'isEnabled': False})

    if app_framework:
        menu_auto_refresh = app_framework.prefs_global.get(
            'menu_auto_refresh', {})
        if menu_auto_refresh.get('main_menu', True):
            try:
                import flame
                flame.schedule_idle_event(rescan_hooks)
            except:
                pass

    if DEBUG:
        print('main menu update took %s' % (time.time() - start))

    return menu
