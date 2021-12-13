import os
import sys
import logging

from Qt import QtWidgets

from avalon import io
from avalon import api as avalon
from openpype import lib
from pyblish import api as pyblish
import openpype.hosts.photoshop

log = logging.getLogger("openpype.hosts.photoshop")

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.photoshop.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")

def check_inventory():
    if not lib.any_outdated():
        return

    host = avalon.registered_host()
    outdated_containers = []
    for container in host.ls():
        representation = container['representation']
        representation_doc = io.find_one(
            {
                "_id": io.ObjectId(representation),
                "type": "representation"
            },
            projection={"parent": True}
        )
        if representation_doc and not lib.is_latest(representation_doc):
            outdated_containers.append(container)

    # Warn about outdated containers.
    print("Starting new QApplication..")
    app = QtWidgets.QApplication(sys.argv)

    message_box = QtWidgets.QMessageBox()
    message_box.setIcon(QtWidgets.QMessageBox.Warning)
    msg = "There are outdated containers in the scene."
    message_box.setText(msg)
    message_box.exec_()

    # Garbage collect QApplication.
    del app


def application_launch():
    check_inventory()


def install():
    print("Installing Pype config...")

    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    log.info(PUBLISH_PATH)

    pyblish.register_callback(
        "instanceToggled", on_pyblish_instance_toggled
    )

    avalon.on("application.launched", application_launch)

def uninstall():
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle layer visibility on instance toggles."""
    instance[0].Visible = new_value
