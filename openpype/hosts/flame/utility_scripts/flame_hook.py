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
    openpype.install()
    avalon.api.install(opflame)
    print("<<<<<<<<<<< Avalon registred hosts: {} >>>>>>>>>>>>>>>".format(
        avalon.api.registered_host()))


# Exception handler
def exeption_handler(exctype, value, tb):
    import traceback
    msg = "OpenPype: Python exception {} in {}".format(value, exctype)
    mbox = QtWidgets.QMessageBox()
    mbox.setText(msg)
    mbox.setDetailedText(
        pformat(traceback.format_exception(exctype, value, tb)))
    mbox.setStyleSheet('QLabel{min-width: 800px;}')
    mbox.exec_()
    sys.__excepthook__(exctype, value, tb)


# add exception handler into sys module
sys.excepthook = exeption_handler


# register clean up logic to be called at Flame exit
def cleanup():
    if opflame.apps:
        print('<<<< `{}` cleaning up apps:\n {}\n'.format(
            __file__, pformat(opflame.apps)))
        while len(opflame.apps):
            app = opflame.apps.pop()
            print('<<<< `{}` removing : {}'.format(__file__, app.name))
            del app
        opflame.apps = []

    if opflame.app_framework:
        print('PYTHON\t: %s cleaning up' % opflame.app_framework.bundle_name)
        opflame.app_framework.save_prefs()
        opflame.app_framework = None


atexit.register(cleanup)


def load_apps():
    opflame.apps.append(opflame.FlameMenuProjectConnect(opflame.app_framework))
    opflame.apps.append(opflame.FlameMenuTimeline(opflame.app_framework))
    opflame.app_framework.log.info("Apps are loaded")


def project_changed_dict(info):
    cleanup()


def app_initialized(parent=None):
    opflame.app_framework = opflame.FlameAppFramework()

    print(">> flame_hook.py: {} initializing".format(
        opflame.app_framework.bundle_name))

    load_apps()


try:
    import flame
    app_initialized(parent=None)
except ImportError:
    print("!!!! not able to import flame module !!!!")


def rescan_hooks():
    flame.execute_shortcut('Rescan Python Hooks')


def _build_app_menu(app_name):
    menu = []
    app = None
    for _app in opflame.apps:
        if _app.__class__.__name__ == app_name:
            app = _app

    if app:
        menu.append(app.build_menu())

    print(">>_> `{}` was build: {}".format(app_name, pformat(menu)))

    if opflame.app_framework:
        menu_auto_refresh = opflame.app_framework.prefs_global.get(
            'menu_auto_refresh', {})
        if menu_auto_refresh.get('timeline_menu', True):
            try:
                import flame
                flame.schedule_idle_event(rescan_hooks)
            except ImportError:
                print("!-!!! not able to import flame module !!!!")

    return menu


def project_saved(project_name, save_time, is_auto_save):
    if opflame.app_framework:
        opflame.app_framework.save_prefs()


def get_main_menu_custom_ui_actions():
    # install openpype and the host
    openpype_install()

    return _build_app_menu("FlameMenuProjectConnect")


def get_timeline_custom_ui_actions():
    # install openpype and the host
    openpype_install()

    return _build_app_menu("FlameMenuTimeline")
