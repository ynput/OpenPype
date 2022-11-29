# -*- coding: utf-8 -*-
"""Pipeline tools for OpenPype Houdini integration."""
import os
import sys
import logging
import contextlib

from openpype.host import HostBase, IWorkfileHost, ILoadHost, INewPublisher
import pyblish.api
from openpype.pipeline import (
    register_creator_plugin_path,
    register_loader_plugin_path,
    AVALON_CONTAINER_ID,
)
from openpype.hosts.max.api import OpenPypeMenu
from openpype.hosts.max.api import lib
from openpype.hosts.max import MAX_HOST_DIR
from openpype.pipeline.load import any_outdated_containers
from openpype.lib import (
    register_event_callback,
    emit_event,
)
from pymxs import runtime as rt  # noqa

log = logging.getLogger("openpype.hosts.max")

PLUGINS_DIR = os.path.join(MAX_HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


class MaxHost(HostBase, IWorkfileHost, ILoadHost, INewPublisher):
    name = "max"
    menu = None

    def __init__(self):
        super(MaxHost, self).__init__()
        self._op_events = {}
        self._has_been_setup = False

    def install(self):
        pyblish.api.register_host("max")

        pyblish.api.register_plugin_path(PUBLISH_PATH)
        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)
        log.info("Building menu ...")

        self.menu = OpenPypeMenu()

        log.info("Installing callbacks ... ")
        # register_event_callback("init", on_init)
        self._register_callbacks()

        # register_event_callback("before.save", before_save)
        # register_event_callback("save", on_save)
        # register_event_callback("open", on_open)
        # register_event_callback("new", on_new)

        # pyblish.api.register_callback(
        #     "instanceToggled", on_pyblish_instance_toggled
        # )

        self._has_been_setup = True

    def has_unsaved_changes(self):
        # TODO: how to get it from 3dsmax?
        return True

    def get_workfile_extensions(self):
        return [".hip", ".hiplc", ".hipnc"]

    def save_workfile(self, dst_path=None):
        rt.saveMaxFile(dst_path)
        return dst_path

    def open_workfile(self, filepath):
        rt.checkForSave()
        rt.loadMaxFile(filepath)
        return filepath

    def get_current_workfile(self):
        return os.path.join(rt.maxFilePath, rt.maxFileName)

    def get_containers(self):
        return ls()

    def _register_callbacks(self):
        for event in self._op_events.copy().values():
            if event is None:
                continue

            try:
                rt.callbacks.removeScript(id=rt.name(event.name))
            except RuntimeError as e:
                log.info(e)

            rt.callbacks.addScript(
                event.name, event.callback, id=rt.Name('OpenPype'))

    @staticmethod
    def create_context_node():
        """Helper for creating context holding node."""

        root_scene = rt.rootScene

        create_attr_script = ("""
attributes "OpenPypeContext"
(
    parameters main rollout:params
    (
        context type: #string
    )
    
    rollout params "OpenPype Parameters"
    (
        editText editTextContext "Context" type: #string
    )
)       
        """)

        attr = rt.execute(create_attr_script)
        rt.custAttributes.add(root_scene, attr)

        return root_scene.OpenPypeContext.context

    def update_context_data(self, data, changes):
        try:
            context = rt.rootScene.OpenPypeContext.context
        except AttributeError:
            # context node doesn't exists
            context = self.create_context_node()

        lib.imprint(context, data)

    def get_context_data(self):
        try:
            context = rt.rootScene.OpenPypeContext.context
        except AttributeError:
            # context node doesn't exists
            context = self.create_context_node()
        return lib.read(context)

    def save_file(self, dst_path=None):
        # Force forwards slashes to avoid segfault
        dst_path = dst_path.replace("\\", "/")
        rt.saveMaxFile(dst_path)


def ls():
    ...