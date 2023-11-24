import json
import base64
import os
import errno
import logging
import contextlib
import shutil

from maya import utils, cmds, OpenMaya
import maya.api.OpenMaya as om

import pyblish.api

from openpype.settings import get_project_settings
from openpype.host import (
    HostBase,
    IWorkfileHost,
    ILoadHost,
    IPublishHost,
    HostDirmap,
)
from openpype.tools.utils import host_tools
from openpype.tools.workfiles.lock_dialog import WorkfileLockDialog
from openpype.lib import (
    register_event_callback,
    emit_event
)
from openpype.pipeline import (
    legacy_io,
    get_current_project_name,
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
    remove_workfile_lock,
    is_workfile_locked,
    is_workfile_lock_enabled
)
from openpype.hosts.maya import MAYA_ROOT_DIR
from openpype.hosts.maya.lib import create_workspace_mel

from . import menu, lib
from .workfile_template_builder import MayaPlaceholderLoadPlugin
from .workio import (
    open_file,
    save_file,
    file_extensions,
    has_unsaved_changes,
    work_root,
    current_file
)

log = logging.getLogger("openpype.hosts.maya")

PLUGINS_DIR = os.path.join(MAYA_ROOT_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")

AVALON_CONTAINERS = ":AVALON_CONTAINERS"


class MayaHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
    name = "maya"

    def __init__(self):
        super(MayaHost, self).__init__()
        self._op_events = {}

    def install(self):
        project_name = get_current_project_name()
        project_settings = get_project_settings(project_name)
        # process path mapping
        dirmap_processor = MayaDirmap("maya", project_name, project_settings)
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

        _set_project()

        if lib.IS_HEADLESS:
            self.log.info((
                "Running in headless mode, skipping Maya save/open/new"
                " callback installation.."
            ))

            return

        self._register_callbacks()

        menu.install(project_settings)

        register_event_callback("save", on_save)
        register_event_callback("open", on_open)
        register_event_callback("new", on_new)
        register_event_callback("before.save", on_before_save)
        register_event_callback("after.save", on_after_save)
        register_event_callback("before.close", on_before_close)
        register_event_callback("before.file.open", before_file_open)
        register_event_callback("taskChanged", on_task_changed)
        register_event_callback("workfile.open.before", before_workfile_open)
        register_event_callback("workfile.save.before", before_workfile_save)
        register_event_callback(
            "workfile.save.before", workfile_save_before_xgen
        )
        register_event_callback("workfile.save.after", after_workfile_save)

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

    def get_workfile_build_placeholder_plugins(self):
        return [
            MayaPlaceholderLoadPlugin
        ]

    @contextlib.contextmanager
    def maintained_selection(self):
        with lib.maintained_selection():
            yield

    def get_context_data(self):
        data = cmds.fileInfo("OpenPypeContext", query=True)
        if not data:
            return {}

        data = data[0]  # Maya seems to return a list
        decoded = base64.b64decode(data).decode("utf-8")
        return json.loads(decoded)

    def update_context_data(self, data, changes):
        json_str = json.dumps(data)
        encoded = base64.b64encode(json_str.encode("utf-8"))
        return cmds.fileInfo("OpenPypeContext", encoded)

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

        self._op_events[_after_scene_save] = (
            OpenMaya.MSceneMessage.addCallback(
                OpenMaya.MSceneMessage.kAfterSave,
                _after_scene_save
            )
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
        self.log.info("Installed event handler _on_after_save..")
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


def _after_scene_save(*arg):
    emit_event("after.save")


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
    """Remove workfile lock on current file"""
    if not handle_workfile_locks():
        return
    filepath = current_file()
    log.info("Removing lock on current file {}...".format(filepath))
    if filepath:
        remove_workfile_lock(filepath)


def handle_workfile_locks():
    if lib.IS_HEADLESS:
        return False
    project_name = get_current_project_name()
    return is_workfile_lock_enabled(MayaHost.name, project_name)


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
        ("loader", loader),
        ("representation", context["representation"]["_id"]),
    ]

    for key, value in data:
        cmds.addAttr(container, longName=key, dataType="string")
        cmds.setAttr(container + "." + key, str(value), type="string")

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

    if not lib.IS_HEADLESS:
        launch_workfiles = os.environ.get("WORKFILES_STARTUP")
        if launch_workfiles:
            safe_deferred(host_tools.show_workfiles)

        from .customize import (
            override_component_mask_commands,
            override_toolbox_ui
        )
        safe_deferred(override_component_mask_commands)
        safe_deferred(override_toolbox_ui)


def on_before_save():
    """Run validation for scene's FPS prior to saving"""
    return lib.validate_fps()


def on_after_save():
    """Check if there is a lockfile after save"""
    check_lock_on_current_file()


def check_lock_on_current_file():

    """Check if there is a user opening the file"""
    if not handle_workfile_locks():
        return
    log.info("Running callback on checking the lock file...")

    # add the lock file when opening the file
    filepath = current_file()
    # Skip if current file is 'untitled'
    if not filepath:
        return

    if is_workfile_locked(filepath):
        # add lockfile dialog
        workfile_dialog = WorkfileLockDialog(filepath)
        if not workfile_dialog.exec_():
            cmds.file(new=True)
            return

    create_workfile_lock(filepath)


def on_before_close():
    """Delete the lock file after user quitting the Maya Scene"""
    log.info("Closing Maya...")
    # delete the lock file
    filepath = current_file()
    if handle_workfile_locks():
        remove_workfile_lock(filepath)


def before_file_open():
    """check lock file when the file changed"""
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

    # Generate ids of the current context on nodes in the scene
    nodes = lib.get_id_required_nodes(referenced_nodes=False)
    for node, new_id in lib.generate_ids(nodes):
        lib.set_id(node, new_id, overwrite=False)


def _update_render_layer_observers():
    # Helper to trigger update for all renderlayer observer logic
    lib.remove_render_layer_observer()
    lib.add_render_layer_observer()
    lib.add_render_layer_change_observer()


def on_open():
    """On scene open let's assume the containers have changed."""

    from openpype.widgets import popup

    utils.executeDeferred(_update_render_layer_observers)

    # Validate FPS after update_task_from_path to
    # ensure it is using correct FPS for the asset
    lib.validate_fps()
    lib.fix_incompatible_containers()

    if any_outdated_containers():
        log.warning("Scene has outdated content.")

        # Find maya main window
        parent = lib.get_main_window()
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
    check_lock_on_current_file()


def on_new():
    """Set project resolution and fps when create a new file"""
    log.info("Running callback on new..")
    with lib.suspended_refresh():
        lib.set_context_settings()

    utils.executeDeferred(_update_render_layer_observers)
    _remove_workfile_lock()


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


def before_workfile_open():
    if handle_workfile_locks():
        _remove_workfile_lock()


def before_workfile_save(event):
    project_name = get_current_project_name()
    if handle_workfile_locks():
        _remove_workfile_lock()
    workdir_path = event["workdir_path"]
    if workdir_path:
        create_workspace_mel(workdir_path, project_name)


def workfile_save_before_xgen(event):
    """Manage Xgen external files when switching context.

    Xgen has various external files that needs to be unique and relative to the
    workfile, so we need to copy and potentially overwrite these files when
    switching context.

    Args:
        event (Event) - openpype/lib/events.py
    """
    if not cmds.pluginInfo("xgenToolkit", query=True, loaded=True):
        return

    import xgenm

    current_work_dir = legacy_io.Session["AVALON_WORKDIR"].replace("\\", "/")
    expected_work_dir = event.data["workdir_path"].replace("\\", "/")
    if current_work_dir == expected_work_dir:
        return

    palettes = cmds.ls(type="xgmPalette", long=True)
    if not palettes:
        return

    transfers = []
    overwrites = []
    attribute_changes = {}
    attrs = ["xgFileName", "xgBaseFile"]
    for palette in palettes:
        sanitized_palette = palette.replace("|", "")
        project_path = xgenm.getAttr("xgProjectPath", sanitized_palette)
        _, maya_extension = os.path.splitext(event.data["filename"])

        for attr in attrs:
            node_attr = "{}.{}".format(palette, attr)
            attr_value = cmds.getAttr(node_attr)

            if not attr_value:
                continue

            source = os.path.join(project_path, attr_value)

            attr_value = event.data["filename"].replace(
                maya_extension,
                "__{}{}".format(
                    sanitized_palette.replace(":", "__"),
                    os.path.splitext(attr_value)[1]
                )
            )
            target = os.path.join(expected_work_dir, attr_value)

            transfers.append((source, target))
            attribute_changes[node_attr] = attr_value

        relative_path = xgenm.getAttr(
            "xgDataPath", sanitized_palette
        ).split(os.pathsep)[0]
        absolute_path = relative_path.replace("${PROJECT}", project_path)
        for root, _, files in os.walk(absolute_path):
            for f in files:
                source = os.path.join(root, f).replace("\\", "/")
                target = source.replace(project_path, expected_work_dir + "/")
                transfers.append((source, target))
                if os.path.exists(target):
                    overwrites.append(target)

    # Ask user about overwriting files.
    if overwrites:
        log.warning(
            "WARNING! Potential loss of data.\n\n"
            "Found duplicate Xgen files in new context.\n{}".format(
                "\n".join(overwrites)
            )
        )
        return

    for source, destination in transfers:
        if not os.path.exists(os.path.dirname(destination)):
            os.makedirs(os.path.dirname(destination))
        shutil.copy(source, destination)

    for attribute, value in attribute_changes.items():
        cmds.setAttr(attribute, value, type="string")


def after_workfile_save(event):
    workfile_name = event["filename"]
    if (
        handle_workfile_locks()
        and workfile_name
        and not is_workfile_locked(workfile_name)
    ):
        create_workfile_lock(workfile_name)


class MayaDirmap(HostDirmap):
    def on_enable_dirmap(self):
        cmds.dirmap(en=True)

    def dirmap_routine(self, source_path, destination_path):
        cmds.dirmap(m=(source_path, destination_path))
        cmds.dirmap(m=(destination_path, source_path))
