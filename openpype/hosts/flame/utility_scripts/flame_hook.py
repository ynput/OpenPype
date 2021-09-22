import sys
from Qt import QtWidgets, QtCore
from pprint import pprint, pformat
import time
import atexit
import openpype
import avalon
import openpype.hosts.flame as opflame

flh = sys.modules[__name__]
flh._project = None


def openpype_install():
    openpype.install()
    avalon.api.install(opflame)
    print("<<<<<<< Avalon registred hosts: {}".format(
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
    opflame.apps.append(opflame.FlameMenuProjectconnect(opflame.app_framework))
    opflame.app_framework.log.info("Apps are loaded")


def project_changed_dict(info):
    cleanup()


def app_initialized():
    opflame.app_framework = opflame.FlameAppFramework()
    print('PYTHON\t: %s initializing' % opflame.app_framework.bundle_name)
    load_apps()


try:
    import flame
    openpype_install()
    app_initialized()
except:
    pass


def project_saved(project_name, save_time, is_auto_save):
    if opflame.app_framework:
        opflame.app_framework.save_prefs()


def get_main_menu_custom_ui_actions():
    # install openpype and the host

    return opflame.main_menu_build(
        opflame.apps, opflame.app_framework)
