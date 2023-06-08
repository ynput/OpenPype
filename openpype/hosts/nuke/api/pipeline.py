import nuke

import os
import importlib
from collections import OrderedDict

import pyblish.api

import openpype
from openpype.host import (
    HostBase,
    IWorkfileHost,
    ILoadHost,
    IPublishHost
)
from openpype.settings import get_current_project_settings
from openpype.lib import register_event_callback, Logger
from openpype.pipeline import (
    register_loader_plugin_path,
    register_creator_plugin_path,
    register_inventory_action_path,
    AVALON_CONTAINER_ID,
)
from openpype.pipeline.workfile import BuildWorkfile
from openpype.tools.utils import host_tools

from .command import viewer_update_and_undo_stop
from .lib import (
    Context,
    ROOT_DATA_KNOB,
    INSTANCE_DATA_KNOB,
    get_main_window,
    add_publish_knob,
    WorkfileSettings,
    process_workfile_builder,
    start_workfile_template_builder,
    launch_workfiles_app,
    check_inventory_versions,
    set_avalon_knob_data,
    read_avalon_data,
    on_script_load,
    dirmap_file_name_filter,
    add_scripts_menu,
    add_scripts_gizmo,
    get_node_data,
    set_node_data
)
from .workfile_template_builder import (
    NukePlaceholderLoadPlugin,
    NukePlaceholderCreatePlugin,
    build_workfile_template,
    create_placeholder,
    update_placeholder,
)
from .workio import (
    open_file,
    save_file,
    file_extensions,
    has_unsaved_changes,
    work_root,
    current_file
)
from .constants import ASSIST

log = Logger.get_logger(__name__)

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.nuke.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")

MENU_LABEL = os.environ["AVALON_LABEL"]

# registering pyblish gui regarding settings in presets
if os.getenv("PYBLISH_GUI", None):
    pyblish.api.register_gui(os.getenv("PYBLISH_GUI", None))


class NukeHost(
    HostBase, IWorkfileHost, ILoadHost, IPublishHost
):
    name = "nuke"

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

    def get_workfile_build_placeholder_plugins(self):
        return [
            NukePlaceholderLoadPlugin,
            NukePlaceholderCreatePlugin
        ]

    def get_containers(self):
        return ls()

    def install(self):
        ''' Installing all requarements for Nuke host
        '''

        pyblish.api.register_host("nuke")

        self.log.info("Registering Nuke plug-ins..")
        pyblish.api.register_plugin_path(PUBLISH_PATH)
        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)
        register_inventory_action_path(INVENTORY_PATH)

        # Register Avalon event for workfiles loading.
        register_event_callback("workio.open_file", check_inventory_versions)
        register_event_callback("taskChanged", change_context_label)

        pyblish.api.register_callback(
            "instanceToggled", on_pyblish_instance_toggled)

        _install_menu()

        # add script menu
        add_scripts_menu()
        add_scripts_gizmo()

        add_nuke_callbacks()

        launch_workfiles_app()

    def get_context_data(self):
        root_node = nuke.root()
        return get_node_data(root_node, ROOT_DATA_KNOB)

    def update_context_data(self, data, changes):
        root_node = nuke.root()
        set_node_data(root_node, ROOT_DATA_KNOB, data)


def add_nuke_callbacks():
    """ Adding all available nuke callbacks
    """
    nuke_settings = get_current_project_settings()["nuke"]
    workfile_settings = WorkfileSettings()
    # Set context settings.
    nuke.addOnCreate(
        workfile_settings.set_context_settings, nodeClass="Root")
    nuke.addOnCreate(workfile_settings.set_favorites, nodeClass="Root")
    nuke.addOnCreate(start_workfile_template_builder, nodeClass="Root")
    nuke.addOnCreate(process_workfile_builder, nodeClass="Root")

    # fix ffmpeg settings on script
    nuke.addOnScriptLoad(on_script_load)

    # set checker for last versions on loaded containers
    nuke.addOnScriptLoad(check_inventory_versions)
    nuke.addOnScriptSave(check_inventory_versions)

    # # set apply all workfile settings on script load and save
    nuke.addOnScriptLoad(WorkfileSettings().set_context_settings)

    if nuke_settings["nuke-dirmap"]["enabled"]:
        log.info("Added Nuke's dirmaping callback ...")
        # Add dirmap for file paths.
        nuke.addFilenameFilter(dirmap_file_name_filter)

    log.info("Added Nuke callbacks ...")


def reload_config():
    """Attempt to reload pipeline at run-time.

    CAUTION: This is primarily for development and debugging purposes.

    """

    for module in (
        "openpype.hosts.nuke.api.actions",
        "openpype.hosts.nuke.api.menu",
        "openpype.hosts.nuke.api.plugin",
        "openpype.hosts.nuke.api.lib",
    ):
        log.info("Reloading module: {}...".format(module))

        module = importlib.import_module(module)

        try:
            importlib.reload(module)
        except AttributeError as e:
            from importlib import reload
            log.warning("Cannot reload module: {}".format(e))
            reload(module)


def _show_workfiles():
    # Make sure parent is not set
    # - this makes Workfiles tool as separated window which
    #   avoid issues with reopening
    # - it is possible to explicitly change on top flag of the tool
    host_tools.show_workfiles(parent=None, on_top=False)


def _install_menu():
    """Install Avalon menu into Nuke's main menu bar."""

    # uninstall original avalon menu
    main_window = get_main_window()
    menubar = nuke.menu("Nuke")
    menu = menubar.addMenu(MENU_LABEL)

    if not ASSIST:
        label = "{0}, {1}".format(
            os.environ["AVALON_ASSET"], os.environ["AVALON_TASK"]
        )
        Context.context_label = label
        context_action = menu.addCommand(label)
        context_action.setEnabled(False)

        # add separator after context label
        menu.addSeparator()

    menu.addCommand(
        "Work Files...",
        _show_workfiles
    )

    menu.addSeparator()
    if not ASSIST:
        menu.addCommand(
            "Create...",
            lambda: host_tools.show_publisher(
                tab="create"
            )
        )
        menu.addCommand(
            "Publish...",
            lambda: host_tools.show_publisher(
                tab="publish"
            )
        )

    menu.addCommand(
        "Load...",
        lambda: host_tools.show_loader(
            parent=main_window,
            use_context=True
        )
    )
    menu.addCommand(
        "Manage...",
        lambda: host_tools.show_scene_inventory(parent=main_window)
    )
    menu.addSeparator()
    menu.addCommand(
        "Library...",
        lambda: host_tools.show_library_loader(
            parent=main_window
        )
    )
    menu.addSeparator()
    menu.addCommand(
        "Set Resolution",
        lambda: WorkfileSettings().reset_resolution()
    )
    menu.addCommand(
        "Set Frame Range",
        lambda: WorkfileSettings().reset_frame_range_handles()
    )
    menu.addCommand(
        "Set Colorspace",
        lambda: WorkfileSettings().set_colorspace()
    )
    menu.addCommand(
        "Apply All Settings",
        lambda: WorkfileSettings().set_context_settings()
    )

    menu.addSeparator()
    menu.addCommand(
        "Build Workfile",
        lambda: BuildWorkfile().process()
    )

    menu_template = menu.addMenu("Template Builder")  # creating template menu
    menu_template.addCommand(
        "Build Workfile from template",
        lambda: build_workfile_template()
    )

    if not ASSIST:
        menu_template.addSeparator()
        menu_template.addCommand(
            "Create Place Holder",
            lambda: create_placeholder()
        )
        menu_template.addCommand(
            "Update Place Holder",
            lambda: update_placeholder()
        )

    menu.addSeparator()
    menu.addCommand(
        "Experimental tools...",
        lambda: host_tools.show_experimental_tools_dialog(parent=main_window)
    )
    menu.addSeparator()
    # add reload pipeline only in debug mode
    if bool(os.getenv("NUKE_DEBUG")):
        menu.addSeparator()
        menu.addCommand("Reload Pipeline", reload_config)

    # adding shortcuts
    add_shortcuts_from_presets()


def change_context_label():
    menubar = nuke.menu("Nuke")
    menu = menubar.findItem(MENU_LABEL)

    label = "{0}, {1}".format(
        os.environ["AVALON_ASSET"], os.environ["AVALON_TASK"]
    )

    rm_item = [
        (i, item) for i, item in enumerate(menu.items())
        if Context.context_label in item.name()
    ][0]

    menu.removeItem(rm_item[1].name())

    context_action = menu.addCommand(
        label,
        index=(rm_item[0])
    )
    context_action.setEnabled(False)

    log.info("Task label changed from `{}` to `{}`".format(
        Context.context_label, label))


def add_shortcuts_from_presets():
    menubar = nuke.menu("Nuke")
    nuke_presets = get_current_project_settings()["nuke"]["general"]

    if nuke_presets.get("menu"):
        menu_label_mapping = {
            "create": "Create...",
            "manage": "Manage...",
            "load": "Load...",
            "build_workfile": "Build Workfile",
            "publish": "Publish..."
        }

        for command_name, shortcut_str in nuke_presets.get("menu").items():
            log.info("menu_name `{}` | menu_label `{}`".format(
                command_name, MENU_LABEL
            ))
            log.info("Adding Shortcut `{}` to `{}`".format(
                shortcut_str, command_name
            ))
            try:
                menu = menubar.findItem(MENU_LABEL)
                item_label = menu_label_mapping[command_name]
                menuitem = menu.findItem(item_label)
                menuitem.setShortcut(shortcut_str)
            except (AttributeError, KeyError) as e:
                log.error(e)


def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle node passthrough states on instance toggles."""

    log.info("instance toggle: {}, old_value: {}, new_value:{} ".format(
        instance, old_value, new_value))

    # Whether instances should be passthrough based on new value

    with viewer_update_and_undo_stop():
        n = instance[0]
        try:
            n["publish"].value()
        except ValueError:
            n = add_publish_knob(n)
            log.info(" `Publish` knob was added to write node..")

        n["publish"].setValue(new_value)


def containerise(node,
                 name,
                 namespace,
                 context,
                 loader=None,
                 data=None):
    """Bundle `node` into an assembly and imprint it with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        node (nuke.Node): Nuke's node object to imprint as container
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        context (dict): Asset information
        loader (str, optional): Name of node used to produce this container.

    Returns:
        node (nuke.Node): containerised nuke's node object

    """
    data = OrderedDict(
        [
            ("schema", "openpype:container-2.0"),
            ("id", AVALON_CONTAINER_ID),
            ("name", name),
            ("namespace", namespace),
            ("loader", str(loader)),
            ("representation", context["representation"]["_id"]),
        ],

        **data or dict()
    )

    set_avalon_knob_data(node, data)

    # set tab to first native
    node.setTab(0)

    return node


def parse_container(node):
    """Returns containerised data of a node

    Reads the imprinted data from `containerise`.

    Arguments:
        node (nuke.Node): Nuke's node object to read imprinted data

    Returns:
        dict: The container schema data for this container node.

    """
    data = read_avalon_data(node)

    # (TODO) Remove key validation when `ls` has re-implemented.
    #
    # If not all required data return the empty container
    required = ["schema", "id", "name",
                "namespace", "loader", "representation"]
    if not all(key in data for key in required):
        return

    # Store the node's name
    data["objectName"] = node["name"].value()

    return data


def update_container(node, keys=None):
    """Returns node with updateted containder data

    Arguments:
        node (nuke.Node): The node in Nuke to imprint as container,
        keys (dict, optional): data which should be updated

    Returns:
        node (nuke.Node): nuke node with updated container data

    Raises:
        TypeError on given an invalid container node

    """
    keys = keys or dict()

    container = parse_container(node)
    if not container:
        raise TypeError("Not a valid container node.")

    container.update(keys)
    node = set_avalon_knob_data(node, container)

    return node


def ls():
    """List available containers.

    This function is used by the Container Manager in Nuke. You'll
    need to implement a for-loop that then *yields* one Container at
    a time.

    See the `container.json` schema for details on how it should look,
    and the Maya equivalent, which is in `avalon.maya.pipeline`
    """
    all_nodes = nuke.allNodes(recurseGroups=False)

    nodes = [n for n in all_nodes]

    for n in nodes:
        container = parse_container(n)
        if container:
            yield container


def list_instances(creator_id=None):
    """List all created instances to publish from current workfile.

    For SubsetManager

    Returns:
        (list) of dictionaries matching instances format
    """
    listed_instances = []
    for node in nuke.allNodes(recurseGroups=True):

        if node.Class() in ["Viewer", "Dot"]:
            continue

        try:
            if node["disable"].value():
                continue
        except NameError:
            # pass if disable knob doesn't exist
            pass

        # get data from avalon knob
        instance_data = get_node_data(
            node, INSTANCE_DATA_KNOB)

        if not instance_data:
            continue

        if instance_data["id"] != "pyblish.avalon.instance":
            continue

        if creator_id and instance_data["creator_identifier"] != creator_id:
            continue

        listed_instances.append((node, instance_data))

    return listed_instances


def remove_instance(instance):
    """Remove instance from current workfile metadata.

    For SubsetManager

    Args:
        instance (dict): instance representation from subsetmanager model
    """
    instance_node = instance.transient_data["node"]
    instance_knob = instance_node.knobs()[INSTANCE_DATA_KNOB]
    instance_node.removeKnob(instance_knob)
    nuke.delete(instance_node)


def select_instance(instance):
    """
        Select instance in Node View

        Args:
            instance (dict): instance representation from subsetmanager model
    """
    instance_node = instance.transient_data["node"]
    instance_node["selected"].setValue(True)
