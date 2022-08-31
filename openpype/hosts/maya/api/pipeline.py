import os
import errno
import logging
import contextlib

from maya import utils, cmds, OpenMaya
import maya.api.OpenMaya as om

import pyblish.api

from openpype.settings import get_project_settings
from openpype.host import HostBase, IWorkfileHost, ILoadHost
import openpype.hosts.maya
from openpype.tools.utils import host_tools
from openpype.lib import (
    register_event_callback,
    emit_event
)
from openpype.lib.path_tools import HostDirmap
from openpype.pipeline import (
    legacy_io,
    register_loader_plugin_path,
    register_inventory_action_path,
    register_creator_plugin_path,
    deregister_loader_plugin_path,
    deregister_inventory_action_path,
    deregister_creator_plugin_path,
    AVALON_CONTAINER_ID,
)
from openpype.pipeline.load import any_outdated_containers
from openpype.pipeline.workfile.lock_workfile import (
    create_workfile_lock,
    get_username,
    remove_workfile_lock,
    is_workfile_locked
)
from openpype.hosts.maya.lib import copy_workspace_mel
from . import menu, lib
from .workio import (
    open_file,
    save_file,
    file_extensions,
    has_unsaved_changes,
    work_root,
    current_file
)

log = logging.getLogger("openpype.hosts.maya")

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.maya.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")

AVALON_CONTAINERS = ":AVALON_CONTAINERS"


class MayaHost(HostBase, IWorkfileHost, ILoadHost):
    name = "maya"

    def __init__(self):
        super(MayaHost, self).__init__()
        self._op_events = {}

    def install(self):
        project_settings = get_project_settings(os.getenv("AVALON_PROJECT"))
        # process path mapping
        dirmap_processor = MayaDirmap("maya", project_settings)
        dirmap_processor.process_dirmap()

        pyblish.api.register_plugin_path(PUBLISH_PATH)
        pyblish.api.register_host("mayabatch")
        pyblish.api.register_host("mayapy")
        pyblish.api.register_host("maya")

        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)
        register_inventory_action_path(INVENTORY_PATH)
        self.log.info(PUBLISH_PATH)

        self.log.info("Installing callbacks ... ")
        register_event_callback("init", on_init)

        if lib.IS_HEADLESS:
            self.log.info((
                "Running in headless mode, skipping Maya save/open/new"
                " callback installation.."
            ))

            return

        _set_project()
        self._register_callbacks()

        menu.install()

        register_event_callback("save", on_save)
        register_event_callback("open", on_open)
        register_event_callback("new", on_new)
        register_event_callback("before.save", on_before_save)
        register_event_callback("before.close", on_before_close)
        register_event_callback("before.file.open", before_file_open)
        register_event_callback("taskChanged", on_task_changed)
        register_event_callback("workfile.open.before", before_workfile_open)
        register_event_callback("workfile.save.before", before_workfile_save)

    def open_workfile(self, filepath):
        return open_file(filepath)

    def save_workfile(self, filepath=None):
        return save_file(filepath)

    def work_root(self, session):
        return work_root(session)

    def get_current_workfile(self):
        return current_file()

    def workfile_has_unsaved_changes(self):
        return has_unsaved_changes()

    def get_workfile_extensions(self):
        return file_extensions()

    def get_containers(self):
        return ls()

    @contextlib.contextmanager
    def maintained_selection(self):
        with lib.maintained_selection():
            yield

    def _register_callbacks(self):
        for handler, event in self._op_events.copy().items():
            if event is None:
                continue

            try:
                OpenMaya.MMessage.removeCallback(event)
                self._op_events[handler] = None
            except RuntimeError as exc:
                self.log.info(exc)

        self._op_events[_on_scene_save] = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kBeforeSave, _on_scene_save
        )

        self._op_events[_before_scene_save] = (
            OpenMaya.MSceneMessage.addCheckCallback(
                OpenMaya.MSceneMessage.kBeforeSaveCheck,
                _before_scene_save
            )
        )

        self._op_events[_on_scene_new] = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kAfterNew, _on_scene_new
        )

        self._op_events[_on_maya_initialized] = (
            OpenMaya.MSceneMessage.addCallback(
                OpenMaya.MSceneMessage.kMayaInitialized,
                _on_maya_initialized
            )
        )

        self._op_events[_on_scene_open] = (
            OpenMaya.MSceneMessage.addCallback(
                OpenMaya.MSceneMessage.kAfterOpen,
                _on_scene_open
            )
        )

        self._op_events[_before_scene_open] = (
            OpenMaya.MSceneMessage.addCallback(
                OpenMaya.MSceneMessage.kBeforeOpen,
                _before_scene_open
            )
        )

        self._op_events[_before_close_maya] = (
            OpenMaya.MSceneMessage.addCallback(
                OpenMaya.MSceneMessage.kMayaExiting,
                _before_close_maya
            )
        )

        self.log.info("Installed event handler _on_scene_save..")
        self.log.info("Installed event handler _before_scene_save..")
        self.log.info("Installed event handler _on_scene_new..")
        self.log.info("Installed event handler _on_maya_initialized..")
        self.log.info("Installed event handler _on_scene_open..")
        self.log.info("Installed event handler _check_lock_file..")
        self.log.info("Installed event handler _before_close_maya..")


def _set_project():
    """Sets the maya project to the current Session's work directory.

    Returns:
        None

    """
    workdir = legacy_io.Session["AVALON_WORKDIR"]

    try:
        os.makedirs(workdir)
    except OSError as e:
        # An already existing working directory is fine.
        if e.errno == errno.EEXIST:
            pass
        else:
            raise

    cmds.workspace(workdir, openWorkspace=True)


def _on_maya_initialized(*args):
    emit_event("init")

    if cmds.about(batch=True):
        log.warning("Running batch mode ...")
        return

    # Keep reference to the main Window, once a main window exists.
    lib.get_main_window()


def _on_scene_new(*args):
    emit_event("new")


def _on_scene_save(*args):
    emit_event("save")


def _on_scene_open(*args):
    emit_event("open")


def _before_close_maya(*args):
    emit_event("before.close")


def _before_scene_open(*args):
    emit_event("before.file.open")


def _before_scene_save(return_code, client_data):

    # Default to allowing the action. Registered
    # callbacks can optionally set this to False
    # in order to block the operation.
    OpenMaya.MScriptUtil.setBool(return_code, True)

    emit_event(
        "before.save",
        {"return_code": return_code}
    )


def _remove_workfile_lock():
    filepath = current_file()
    if filepath:
        remove_workfile_lock(filepath)


def uninstall():
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    pyblish.api.deregister_host("mayabatch")
    pyblish.api.deregister_host("mayapy")
    pyblish.api.deregister_host("maya")

    deregister_loader_plugin_path(LOAD_PATH)
    deregister_creator_plugin_path(CREATE_PATH)
    deregister_inventory_action_path(INVENTORY_PATH)

    menu.uninstall()


def parse_container(container):
    """Return the container node's full container data.

    Args:
        container (str): A container node name.

    Returns:
        dict: The container schema data for this container node.

    """
    data = lib.read(container)

    # Backwards compatibility pre-schemas for containers
    data["schema"] = data.get("schema", "openpype:container-1.0")

    # Append transient data
    data["objectName"] = container

    return data


def _ls():
    """Yields Avalon container node names.

    Used by `ls()` to retrieve the nodes and then query the full container's
    data.

    Yields:
        str: Avalon container node name (objectSet)

    """

    def _maya_iterate(iterator):
        """Helper to iterate a maya iterator"""
        while not iterator.isDone():
            yield iterator.thisNode()
            iterator.next()

    ids = {AVALON_CONTAINER_ID,
           # Backwards compatibility
           "pyblish.mindbender.container"}

    # Iterate over all 'set' nodes in the scene to detect whether
    # they have the avalon container ".id" attribute.
    fn_dep = om.MFnDependencyNode()
    iterator = om.MItDependencyNodes(om.MFn.kSet)
    for mobject in _maya_iterate(iterator):
        if mobject.apiTypeStr != "kSet":
            # Only match by exact type
            continue

        fn_dep.setObject(mobject)
        if not fn_dep.hasAttribute("id"):
            continue

        plug = fn_dep.findPlug("id", True)
        value = plug.asString()
        if value in ids:
            yield fn_dep.name()


def ls():
    """Yields containers from active Maya scene

    This is the host-equivalent of api.ls(), but instead of listing
    assets on disk, it lists assets already loaded in Maya; once loaded
    they are called 'containers'

    Yields:
        dict: container

    """
    container_names = _ls()
    for container in sorted(container_names):
        yield parse_container(container)


def containerise(name,
                 namespace,
                 nodes,
                 context,
                 loader=None,
                 suffix="CON"):
    """Bundle `nodes` into an assembly and imprint it with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        nodes (list): Long names of nodes to containerise
        context (dict): Asset information
        loader (str, optional): Name of loader used to produce this container.
        suffix (str, optional): Suffix of container, defaults to `_CON`.

    Returns:
        container (str): Name of container assembly

    """
    container = cmds.sets(nodes, name="%s_%s_%s" % (namespace, name, suffix))

    data = [
        ("schema", "openpype:container-2.0"),
        ("id", AVALON_CONTAINER_ID),
        ("name", name),
        ("namespace", namespace),
        ("loader", str(loader)),
        ("representation", context["representation"]["_id"]),
    ]

    for key, value in data:
        if not value:
            continue

        if isinstance(value, (int, float)):
            cmds.addAttr(container, longName=key, attributeType="short")
            cmds.setAttr(container + "." + key, value)

        else:
            cmds.addAttr(container, longName=key, dataType="string")
            cmds.setAttr(container + "." + key, value, type="string")

    main_container = cmds.ls(AVALON_CONTAINERS, type="objectSet")
    if not main_container:
        main_container = cmds.sets(empty=True, name=AVALON_CONTAINERS)

        # Implement #399: Maya 2019+ hide AVALON_CONTAINERS on creation..
        if cmds.attributeQuery("hiddenInOutliner",
                               node=main_container,
                               exists=True):
            cmds.setAttr(main_container + ".hiddenInOutliner", True)
    else:
        main_container = main_container[0]

    cmds.sets(container, addElement=main_container)

    # Implement #399: Maya 2019+ hide containers in outliner
    if cmds.attributeQuery("hiddenInOutliner",
                           node=container,
                           exists=True):
        cmds.setAttr(container + ".hiddenInOutliner", True)

    return container


def on_init():
    log.info("Running callback on init..")

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

    if not lib.IS_HEADLESS:
        safe_deferred(override_toolbox_ui)


def on_before_save():
    """Run validation for scene's FPS prior to saving"""
    return lib.validate_fps()


def after_file_open():
    """Check if there is a user opening the file"""
    log.info("Running callback on checking the lock file...")

    # add the lock file when opening the file
    filepath = current_file()

    if not is_workfile_locked(filepath):
        create_workfile_lock(filepath)

    else:
        username = get_username(filepath)
        reminder = cmds.window(title="Reminder", width=400, height=30)
        cmds.columnLayout(adjustableColumn=True)
        cmds.separator()
        cmds.columnLayout(adjustableColumn=True)
        comment = " %s is working the same workfile!" % username
        cmds.text(comment, align='center')
        cmds.text(vis=False)
        cmds.rowColumnLayout(numberOfColumns=3,
                             columnWidth=[(1, 300), (2, 100)],
                             columnSpacing=[(2, 10)])
        cmds.separator(vis=False)
        quit_command = "cmds.quit(force=True);cmds.deleteUI('%s')" % reminder
        cmds.button(label='Ok', command=quit_command)
        cmds.showWindow(reminder)


def on_before_close():
    """Delete the lock file after user quitting the Maya Scene"""
    log.info("Closing Maya...")
    # delete the lock file
    filepath = current_file()
    remove_workfile_lock(filepath)


def before_file_open():
    """check lock file when the file changed"""
    log.info("check lock file when file changed...")
    # delete the lock file
    _remove_workfile_lock()


def on_save():
    """Automatically add IDs to new nodes

    Any transform of a mesh, without an existing ID, is given one
    automatically on file save.
    """

    log.info("Running callback on save..")
    # remove lockfile if users jumps over from one scene to another
    _remove_workfile_lock()

    # # Update current task for the current scene
    # update_task_from_path(cmds.file(query=True, sceneName=True))

    # Generate ids of the current context on nodes in the scene
    nodes = lib.get_id_required_nodes(referenced_nodes=False)
    for node, new_id in lib.generate_ids(nodes):
        lib.set_id(node, new_id, overwrite=False)


def on_open():
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

    if any_outdated_containers():
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
            dialog.on_clicked.connect(_on_show_inventory)
            dialog.show()

    # create lock file for the maya scene
    after_file_open()


def on_new():
    """Set project resolution and fps when create a new file"""
    log.info("Running callback on new..")
    with lib.suspended_refresh():
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


def on_task_changed():
    """Wrapped function of app initialize and maya's on task changed"""
    # Run
    menu.update_menu_task_label()

    workdir = legacy_io.Session["AVALON_WORKDIR"]
    if os.path.exists(workdir):
        log.info("Updating Maya workspace for task change to %s", workdir)
        _set_project()

        # Set Maya fileDialog's start-dir to /scenes
        frule_scene = cmds.workspace(fileRuleEntry="scene")
        cmds.optionVar(stringValue=("browserLocationmayaBinaryscene",
                                    workdir + "/" + frule_scene))

    else:
        log.warning((
            "Can't set project for new context because path does not exist: {}"
        ).format(workdir))

    with lib.suspended_refresh():
        lib.set_context_settings()
        lib.update_content_on_context_change()

    msg = "  project: {}\n  asset: {}\n  task:{}".format(
        legacy_io.Session["AVALON_PROJECT"],
        legacy_io.Session["AVALON_ASSET"],
        legacy_io.Session["AVALON_TASK"]
    )

    lib.show_message(
        "Context was changed",
        ("Context was changed to:\n{}".format(msg)),
    )


def before_workfile_open():
    _remove_workfile_lock()


def before_workfile_save(event):
    _remove_workfile_lock()
    workdir_path = event["workdir_path"]
    if workdir_path:
        copy_workspace_mel(workdir_path)


class MayaDirmap(HostDirmap):
    def on_enable_dirmap(self):
        cmds.dirmap(en=True)

    def dirmap_routine(self, source_path, destination_path):
        cmds.dirmap(m=(source_path, destination_path))
        cmds.dirmap(m=(destination_path, source_path))
