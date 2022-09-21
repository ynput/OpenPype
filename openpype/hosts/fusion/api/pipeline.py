"""
Basic avalon integration
"""
import os
import logging
import contextlib

import pyblish.api

from openpype.lib import (
    Logger,
    register_event_callback
)
from openpype.pipeline import (
    register_loader_plugin_path,
    register_creator_plugin_path,
    register_inventory_action_path,
    AVALON_CONTAINER_ID,
)
from openpype.pipeline.load import any_outdated_containers
from openpype.hosts.fusion import FUSION_HOST_DIR
from openpype.host import HostBase, IWorkfileHost, ILoadHost, INewPublisher
from openpype.tools.utils import host_tools


from .lib import (
    get_current_comp,
    comp_lock_and_undo_chunk,
    validate_comp_prefs
)

log = Logger.get_logger(__name__)

PLUGINS_DIR = os.path.join(FUSION_HOST_DIR, "plugins")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


class CompLogHandler(logging.Handler):
    def emit(self, record):
        entry = self.format(record)
        comp = get_current_comp()
        if comp:
            comp.Print(entry)


class FusionHost(HostBase, IWorkfileHost, ILoadHost, INewPublisher):
    name = "fusion"

    def install(self):
        """Install fusion-specific functionality of OpenPype.

        This is where you install menus and register families, data
        and loaders into fusion.

        It is called automatically when installing via
        `openpype.pipeline.install_host(openpype.hosts.fusion.api)`

        See the Maya equivalent for inspiration on how to implement this.

        """
        # Remove all handlers associated with the root logger object, because
        # that one always logs as "warnings" incorrectly.
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        # Attach default logging handler that prints to active comp
        logger = logging.getLogger()
        formatter = logging.Formatter(fmt="%(message)s\n")
        handler = CompLogHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        pyblish.api.register_host("fusion")
        pyblish.api.register_plugin_path(PUBLISH_PATH)
        log.info("Registering Fusion plug-ins..")

        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)
        register_inventory_action_path(INVENTORY_PATH)

        pyblish.api.register_callback("instanceToggled",
                                      on_pyblish_instance_toggled)

        # Fusion integration currently does not attach to direct callbacks of
        # the application. So we use workfile callbacks to allow similar
        # behavior on save and open
        register_event_callback("workfile.open.after", on_after_open)

    # region workfile io api
    def has_unsaved_changes(self):
        comp = get_current_comp()
        return comp.GetAttrs()["COMPB_Modified"]

    def get_workfile_extensions(self):
        return [".comp"]

    def save_workfile(self, dst_path=None):
        comp = get_current_comp()
        comp.Save(dst_path)

    def open_workfile(self, filepath):
        # Hack to get fusion, see
        #   openpype.hosts.fusion.api.pipeline.get_current_comp()
        fusion = getattr(sys.modules["__main__"], "fusion", None)

        return fusion.LoadComp(filepath)

    def get_current_workfile(self):
        comp = get_current_comp()
        current_filepath = comp.GetAttrs()["COMPS_FileName"]
        if not current_filepath:
            return None

        return current_filepath

    def work_root(self, session):
        work_dir = session["AVALON_WORKDIR"]
        scene_dir = session.get("AVALON_SCENEDIR")
        if scene_dir:
            return os.path.join(work_dir, scene_dir)
        else:
            return work_dir
    # endregion

    @contextlib.contextmanager
    def maintained_selection(self):
        from .lib import maintained_selection
        return maintained_selection()

    def get_containers(self):
        return ls()

    def update_context_data(self, data, changes):
        print(data, changes)

    def get_context_data(self):
        return {}


def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle saver tool passthrough states on instance toggles."""
    comp = instance.context.data.get("currentComp")
    if not comp:
        return

    savers = [tool for tool in instance if
              getattr(tool, "ID", None) == "Saver"]
    if not savers:
        return

    # Whether instances should be passthrough based on new value
    passthrough = not new_value
    with comp_lock_and_undo_chunk(comp,
                                  undo_queue_name="Change instance "
                                                  "active state"):
        for tool in savers:
            attrs = tool.GetAttrs()
            current = attrs["TOOLB_PassThrough"]
            if current != passthrough:
                tool.SetAttrs({"TOOLB_PassThrough": passthrough})


def on_after_open(_event):
    comp = get_current_comp()
    validate_comp_prefs(comp)

    if any_outdated_containers():
        log.warning("Scene has outdated content.")

        # Find OpenPype menu to attach to
        from . import menu

        def _on_show_scene_inventory():
            # ensure that comp is active
            frame = comp.CurrentFrame
            if not frame:
                print("Comp is closed, skipping show scene inventory")
                return
            frame.ActivateFrame()   # raise comp window
            host_tools.show_scene_inventory()

        from openpype.widgets import popup
        from openpype.style import load_stylesheet
        dialog = popup.Popup(parent=menu.menu)
        dialog.setWindowTitle("Fusion comp has outdated content")
        dialog.setMessage("There are outdated containers in "
                          "your Fusion comp.")
        dialog.on_clicked.connect(_on_show_scene_inventory)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.setStyleSheet(load_stylesheet())


def ls():
    """List containers from active Fusion scene

    This is the host-equivalent of api.ls(), but instead of listing
    assets on disk, it lists assets already loaded in Fusion; once loaded
    they are called 'containers'

    Yields:
        dict: container

    """

    comp = get_current_comp()
    tools = comp.GetToolList(False, "Loader").values()

    for tool in tools:
        container = parse_container(tool)
        if container:
            yield container


def imprint_container(tool,
                      name,
                      namespace,
                      context,
                      loader=None):
    """Imprint a Loader with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        tool (object): The node in Fusion to imprint as container, usually a
            Loader.
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        context (dict): Asset information
        loader (str, optional): Name of loader used to produce this container.

    Returns:
        None

    """

    data = [
        ("schema", "openpype:container-2.0"),
        ("id", AVALON_CONTAINER_ID),
        ("name", str(name)),
        ("namespace", str(namespace)),
        ("loader", str(loader)),
        ("representation", str(context["representation"]["_id"])),
    ]

    for key, value in data:
        tool.SetData("avalon.{}".format(key), value)


def parse_container(tool):
    """Returns imprinted container data of a tool

    This reads the imprinted data from `imprint_container`.

    """

    data = tool.GetData('avalon')
    if not isinstance(data, dict):
        return

    # If not all required data return the empty container
    required = ['schema', 'id', 'name',
                'namespace', 'loader', 'representation']
    if not all(key in data for key in required):
        return

    container = {key: data[key] for key in required}

    # Store the tool's name
    container["objectName"] = tool.Name

    # Store reference to the tool object
    container["_tool"] = tool

    return container


# TODO: Function below is currently unused prototypes
def list_instances(creator_id=None):
    """Return created instances in current workfile which will be published.

    Returns:
        (list) of dictionaries matching instances format
    """

    comp = get_current_comp()
    tools = comp.GetToolList(False).values()

    instance_signature = {
        "id": "pyblish.avalon.instance",
        "identifier": creator_id
    }
    instances = []
    for tool in tools:

        data = tool.GetData('openpype')
        if not isinstance(data, dict):
            continue

        if data.get("id") != instance_signature["id"]:
            continue

        if creator_id and data.get("identifier") != creator_id:
            continue

        instances.append(tool)

    return instances


# TODO: Function below is currently unused prototypes
def remove_instance(instance):
    """Remove instance from current workfile.

    Args:
        instance (dict): instance representation from subsetmanager model
    """
    # Assume instance is a Fusion tool directly
    instance["tool"].Delete()
