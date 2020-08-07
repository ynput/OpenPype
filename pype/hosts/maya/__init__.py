import os
import logging
import weakref

from maya import utils, cmds

from avalon import api as avalon, pipeline, maya
from avalon.maya.pipeline import IS_HEADLESS
from avalon.tools import workfiles
from pyblish import api as pyblish

from ...lib import any_outdated
from pype import PLUGINS_DIR

from . import menu
from . import lib

log = logging.getLogger("pype.hosts.maya")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "maya", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "maya", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "maya", "create")


def install():
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    log.info(PUBLISH_PATH)
    menu.install()

    log.info("Installing callbacks ... ")
    avalon.on("init", on_init)

    # Callbacks below are not required for headless mode, the `init` however
    # is important to load referenced Alembics correctly at rendertime.
    if IS_HEADLESS:
        log.info("Running in headless mode, skipping Colorbleed Maya "
                 "save/open/new callback installation..")
        return

    avalon.on("save", on_save)
    avalon.on("open", on_open)
    avalon.on("new", on_new)
    avalon.before("save", on_before_save)

    log.info("Overriding existing event 'taskChanged'")
    override_event("taskChanged", on_task_changed)

    log.info("Setting default family states for loader..")
    avalon.data["familiesStateToggled"] = ["imagesequence"]


def uninstall():
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    menu.uninstall()


def override_event(event, callback):
    """
    Override existing event callback
    Args:
        event (str): name of the event
        callback (function): callback to be triggered

    Returns:
        None

    """

    ref = weakref.WeakSet()
    ref.add(callback)

    pipeline._registered_event_handlers[event] = ref


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
        safe_deferred(launch_workfiles_app)

    if not IS_HEADLESS:
        safe_deferred(override_toolbox_ui)


def launch_workfiles_app(*args):
    workfiles.show(os.environ["AVALON_WORKDIR"])


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

    from avalon.vendor.Qt import QtWidgets
    from ...widgets import popup

    cmds.evalDeferred(
        "from pype.hosts.maya import lib;lib.remove_render_layer_observer()")
    cmds.evalDeferred(
        "from pype.hosts.maya import lib;lib.add_render_layer_observer()")
    cmds.evalDeferred(
        "from pype.hosts.maya import lib;lib.add_render_layer_change_observer()")
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
                import avalon.tools.sceneinventory as tool
                tool.show(parent=parent)

            dialog = popup.Popup(parent=parent)
            dialog.setWindowTitle("Maya scene has outdated content")
            dialog.setMessage("There are outdated containers in "
                              "your Maya scene.")
            dialog.on_show.connect(_on_show_inventory)
            dialog.show()


def on_new(_):
    """Set project resolution and fps when create a new file"""
    avalon.logger.info("Running callback on new..")
    with maya.suspended_refresh():
        cmds.evalDeferred(
            "from pype.hosts.maya import lib;lib.remove_render_layer_observer()")
        cmds.evalDeferred(
            "from pype.hosts.maya import lib;lib.add_render_layer_observer()")
        cmds.evalDeferred(
            "from pype.hosts.maya import lib;lib.add_render_layer_change_observer()")
        lib.set_context_settings()


def on_task_changed(*args):
    """Wrapped function of app initialize and maya's on task changed"""

    # Inputs (from the switched session and running app)
    session = avalon.Session.copy()
    app_name = os.environ["AVALON_APP_NAME"]

    # Find the application definition
    app_definition = pipeline.lib.get_application(app_name)

    App = type("app_%s" % app_name,
               (avalon.Application,),
               {"config": app_definition.copy()})

    # Initialize within the new session's environment
    app = App()
    env = app.environ(session)
    app.initialize(env)

    # Run
    maya.pipeline._on_task_changed()
    with maya.suspended_refresh():
        lib.set_context_settings()
        lib.update_content_on_context_change()

    lib.show_message("Context was changed",
                     ("Context was changed to {}".format(
                        avalon.Session["AVALON_ASSET"])))
