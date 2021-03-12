import os
import sys
import nuke
import getpass
from pype.api import Anatomy
from avalon.nuke import (
    save_file, open_file
)
from avalon import (
    io, api
)
from avalon.tools import workfiles
from pyblish import api as pyblish
from pype.hosts.nuke import menu
from pype.api import Logger
from pype import PLUGINS_DIR
from . import lib


self = sys.modules[__name__]
self.workfiles_launched = False
log = Logger().get_logger(__name__, "nuke")

AVALON_CONFIG = os.getenv("AVALON_CONFIG", "pype")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "nuke", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "nuke", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "nuke", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "nuke", "inventory")


# registering pyblish gui regarding settings in presets
if os.getenv("PYBLISH_GUI", None):
    pyblish.register_gui(os.getenv("PYBLISH_GUI", None))


def reload_config():
    """Attempt to reload pipeline at run-time.

    CAUTION: This is primarily for development and debugging purposes.

    """

    import importlib

    for module in (
        "{}.api".format(AVALON_CONFIG),
        "{}.hosts.nuke.actions".format(AVALON_CONFIG),
        "{}.hosts.nuke.presets".format(AVALON_CONFIG),
        "{}.hosts.nuke.menu".format(AVALON_CONFIG),
        "{}.hosts.nuke.plugin".format(AVALON_CONFIG),
        "{}.hosts.nuke.lib".format(AVALON_CONFIG),
    ):
        log.info("Reloading module: {}...".format(module))

        module = importlib.import_module(module)

        try:
            importlib.reload(module)
        except AttributeError as e:
            log.warning("Cannot reload module: {}".format(e))
            reload(module)


def install():
    ''' Installing all requarements for Nuke host
    '''

    log.info("Registering Nuke plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    api.register_plugin_path(api.Loader, LOAD_PATH)
    api.register_plugin_path(api.Creator, CREATE_PATH)
    api.register_plugin_path(api.InventoryAction, INVENTORY_PATH)

    # Register Avalon event for workfiles loading.
    api.on("workio.open_file", lib.check_inventory_versions)

    pyblish.register_callback("instanceToggled", on_pyblish_instance_toggled)
    workfile_settings = lib.WorkfileSettings()
    # Disable all families except for the ones we explicitly want to see
    family_states = [
        "write",
        "review",
        "nukenodes"
        "gizmo"
    ]

    api.data["familiesStateDefault"] = False
    api.data["familiesStateToggled"] = family_states

    # Set context settings.
    nuke.addOnCreate(workfile_settings.set_context_settings, nodeClass="Root")
    nuke.addOnCreate(workfile_settings.set_favorites, nodeClass="Root")
    nuke.addOnCreate(open_last_workfile, nodeClass="Root")
    nuke.addOnCreate(launch_workfiles_app, nodeClass="Root")
    menu.install()


def launch_workfiles_app():
    '''Function letting start workfiles after start of host
    '''
    if not os.environ.get("WORKFILES_STARTUP"):
        return

    if not self.workfiles_launched:
        self.workfiles_launched = True
        workfiles.show(os.environ["AVALON_WORKDIR"])


def open_last_workfile():
    if not os.getenv("WORKFILE_OPEN_LAST_VERSION"):
        return

    log.info("Opening last workfile...")
    last_workfile_path = os.environ.get("AVALON_LAST_WORKFILE")
    if not last_workfile_path:
        root_path = api.registered_root()
        workdir = os.environ["AVALON_WORKDIR"]
        task = os.environ["AVALON_TASK"]
        project_name = os.environ["AVALON_PROJECT"]
        asset_name = os.environ["AVALON_ASSET"]

        io.install()
        project_entity = io.find_one({
            "type": "project",
            "name": project_name
        })
        assert project_entity, (
            "Project '{0}' was not found."
        ).format(project_name)

        asset_entity = io.find_one({
            "type": "asset",
            "name": asset_name,
            "parent": project_entity["_id"]
        })
        assert asset_entity, (
            "No asset found by the name '{0}' in project '{1}'"
        ).format(asset_name, project_name)

        project_name = project_entity["name"]

        anatomy = Anatomy()
        file_template = anatomy.templates["work"]["file"]
        extensions = api.HOST_WORKFILE_EXTENSIONS.get("nuke")

        # create anatomy data for building file name
        workdir_data = {
            "root": root_path,
            "project": {
                "name": project_name,
                "code": project_entity["data"].get("code")
            },
            "asset": asset_entity["name"],
            "task": task,
            "version": 1,
            "user": os.environ.get("PYPE_USERNAME") or getpass.getuser(),
            "ext": extensions[0]
        }

        # create last workfile name
        last_workfile_path = api.last_workfile(
            workdir, file_template, workdir_data, extensions, True
        )
    if not os.path.exists(last_workfile_path):
        save_file(last_workfile_path)
    else:
        # to avoid looping of the callback, remove it!
        nuke.removeOnCreate(open_last_workfile, nodeClass="Root")

        # open workfile
        open_file(last_workfile_path)


def uninstall():
    '''Uninstalling host's integration
    '''
    log.info("Deregistering Nuke plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    api.deregister_plugin_path(api.Loader, LOAD_PATH)
    api.deregister_plugin_path(api.Creator, CREATE_PATH)

    pyblish.deregister_callback("instanceToggled", on_pyblish_instance_toggled)


    reload_config()
    menu.uninstall()


def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle node passthrough states on instance toggles."""

    log.info("instance toggle: {}, old_value: {}, new_value:{} ".format(
        instance, old_value, new_value))

    from avalon.nuke import (
        viewer_update_and_undo_stop,
        add_publish_knob
    )

    # Whether instances should be passthrough based on new value

    with viewer_update_and_undo_stop():
        n = instance[0]
        try:
            n["publish"].value()
        except ValueError:
            n = add_publish_knob(n)
            log.info(" `Publish` knob was added to write node..")

        n["publish"].setValue(new_value)
