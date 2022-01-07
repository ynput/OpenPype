import os
import logging
import weakref

from maya import utils, cmds

from avalon import api as avalon
from avalon import pipeline
from avalon.maya import suspended_refresh
from avalon.maya.pipeline import IS_HEADLESS
from openpype.tools.utils import host_tools
from pyblish import api as pyblish
from openpype.lib import any_outdated
import openpype.hosts.maya
from openpype.hosts.maya.lib import copy_workspace_mel
from openpype.lib.path_tools import HostDirmap
from . import menu, lib

log = logging.getLogger("openpype.hosts.maya")

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.maya.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


def install():
    from openpype.settings import get_project_settings

    project_settings = get_project_settings(os.getenv("AVALON_PROJECT"))
    # process path mapping
    dirmap_processor = MayaDirmap("maya", project_settings)
    dirmap_processor.process_dirmap()

    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)
    log.info(PUBLISH_PATH)
    menu.install()

    log.info("Installing callbacks ... ")
    avalon.on("init", on_init)

    # Callbacks below are not required for headless mode, the `init` however
    # is important to load referenced Alembics correctly at rendertime.
    if IS_HEADLESS:
        log.info("Running in headless mode, skipping Maya "
                 "save/open/new callback installation..")
        return

    avalon.on("save", on_save)
    avalon.on("open", on_open)
    avalon.on("new", on_new)
    avalon.before("save", on_before_save)
    avalon.on("taskChanged", on_task_changed)
    avalon.on("before.workfile.save", before_workfile_save)

    log.info("Setting default family states for loader..")
    avalon.data["familiesStateToggled"] = ["imagesequence"]


def uninstall():
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.deregister_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    menu.uninstall()


def on_init(_):
    avalon.logger.info("Running callback on init..")

    def safe_deferred(fn):
        """Execute deferred the function in a try-except"""

        def _fn():
            """safely call in deferred callback"""
            try:
                fn()
            except Exception as exc:
                print(exc)

        try:
            utils.executeDeferred(_fn)
        except Exception as exc:
            print(exc)

    # Force load Alembic so referenced alembics
    # work correctly on scene open
    cmds.loadPlugin("AbcImport", quiet=True)
    cmds.loadPlugin("AbcExport", quiet=True)

    # Force load objExport plug-in (requested by artists)
    cmds.loadPlugin("objExport", quiet=True)

    from .customize import (
        override_component_mask_commands,
        override_toolbox_ui
    )
    safe_deferred(override_component_mask_commands)

    launch_workfiles = os.environ.get("WORKFILES_STARTUP")

    if launch_workfiles:
        safe_deferred(host_tools.show_workfiles)

    if not IS_HEADLESS:
        safe_deferred(override_toolbox_ui)


def on_before_save(return_code, _):
    """Run validation for scene's FPS prior to saving"""
    return lib.validate_fps()


def on_save(_):
    """Automatically add IDs to new nodes

    Any transform of a mesh, without an existing ID, is given one
    automatically on file save.
    """

    avalon.logger.info("Running callback on save..")

    # # Update current task for the current scene
    # update_task_from_path(cmds.file(query=True, sceneName=True))

    # Generate ids of the current context on nodes in the scene
    nodes = lib.get_id_required_nodes(referenced_nodes=False)
    for node, new_id in lib.generate_ids(nodes):
        lib.set_id(node, new_id, overwrite=False)


def on_open(_):
    """On scene open let's assume the containers have changed."""

    from Qt import QtWidgets
    from openpype.widgets import popup

    cmds.evalDeferred(
        "from openpype.hosts.maya.api import lib;"
        "lib.remove_render_layer_observer()")
    cmds.evalDeferred(
        "from openpype.hosts.maya.api import lib;"
        "lib.add_render_layer_observer()")
    cmds.evalDeferred(
        "from openpype.hosts.maya.api import lib;"
        "lib.add_render_layer_change_observer()")
    # # Update current task for the current scene
    # update_task_from_path(cmds.file(query=True, sceneName=True))

    # Validate FPS after update_task_from_path to
    # ensure it is using correct FPS for the asset
    lib.validate_fps()
    lib.fix_incompatible_containers()

    if any_outdated():
        log.warning("Scene has outdated content.")

        # Find maya main window
        top_level_widgets = {w.objectName(): w for w in
                             QtWidgets.QApplication.topLevelWidgets()}
        parent = top_level_widgets.get("MayaWindow", None)

        if parent is None:
            log.info("Skipping outdated content pop-up "
                     "because Maya window can't be found.")
        else:

            # Show outdated pop-up
            def _on_show_inventory():
                host_tools.show_scene_inventory(parent=parent)

            dialog = popup.Popup(parent=parent)
            dialog.setWindowTitle("Maya scene has outdated content")
            dialog.setMessage("There are outdated containers in "
                              "your Maya scene.")
            dialog.on_show.connect(_on_show_inventory)
            dialog.show()


def on_new(_):
    """Set project resolution and fps when create a new file"""
    avalon.logger.info("Running callback on new..")
    with suspended_refresh():
        cmds.evalDeferred(
            "from openpype.hosts.maya.api import lib;"
            "lib.remove_render_layer_observer()")
        cmds.evalDeferred(
            "from openpype.hosts.maya.api import lib;"
            "lib.add_render_layer_observer()")
        cmds.evalDeferred(
            "from openpype.hosts.maya.api import lib;"
            "lib.add_render_layer_change_observer()")
        lib.set_context_settings()


def on_task_changed(*args):
    """Wrapped function of app initialize and maya's on task changed"""
    # Run
    with suspended_refresh():
        lib.set_context_settings()
        lib.update_content_on_context_change()

    msg = "  project: {}\n  asset: {}\n  task:{}".format(
        avalon.Session["AVALON_PROJECT"],
        avalon.Session["AVALON_ASSET"],
        avalon.Session["AVALON_TASK"]
    )

    lib.show_message(
        "Context was changed",
        ("Context was changed to:\n{}".format(msg)),
    )


def before_workfile_save(workfile_path, workdir_path):
    if workdir_path:
        copy_workspace_mel(workdir_path)


class MayaDirmap(HostDirmap):
    def on_enable_dirmap(self):
        cmds.dirmap(en=True)

    def dirmap_routine(self, source_path, destination_path):
        cmds.dirmap(m=(source_path, destination_path))
        cmds.dirmap(m=(destination_path, source_path))
