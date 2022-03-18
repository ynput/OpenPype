"""
Basic avalon integration
"""
import os
import contextlib
from avalon import api as avalon
from avalon.pipeline import AVALON_CONTAINER_ID
from pyblish import api as pyblish
from openpype.api import Logger
from openpype.pipeline import (
    LegacyCreator,
    register_loader_plugin_path,
    deregister_loader_plugin_path,
)
from .lib import (
    set_segment_data_marker,
    set_publish_attribute,
    maintained_segment_selection,
    get_current_sequence,
    reset_segment_selection
)
from .. import HOST_DIR

API_DIR = os.path.join(HOST_DIR, "api")
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")

AVALON_CONTAINERS = "AVALON_CONTAINERS"

log = Logger.get_logger(__name__)


def install():
    pyblish.register_host("flame")
    pyblish.register_plugin_path(PUBLISH_PATH)
    register_loader_plugin_path(LOAD_PATH)
    avalon.register_plugin_path(LegacyCreator, CREATE_PATH)
    log.info("OpenPype Flame plug-ins registred ...")

    # register callback for switching publishable
    pyblish.register_callback("instanceToggled", on_pyblish_instance_toggled)

    log.info("OpenPype Flame host installed ...")


def uninstall():
    pyblish.deregister_host("flame")

    log.info("Deregistering Flame plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    deregister_loader_plugin_path(LOAD_PATH)
    avalon.deregister_plugin_path(LegacyCreator, CREATE_PATH)

    # register callback for switching publishable
    pyblish.deregister_callback("instanceToggled", on_pyblish_instance_toggled)

    log.info("OpenPype Flame host uninstalled ...")


def containerise(flame_clip_segment,
                 name,
                 namespace,
                 context,
                 loader=None,
                 data=None):

    data_imprint = {
        "schema": "openpype:container-2.0",
        "id": AVALON_CONTAINER_ID,
        "name": str(name),
        "namespace": str(namespace),
        "loader": str(loader),
        "representation": str(context["representation"]["_id"]),
    }

    if data:
        for k, v in data.items():
            data_imprint[k] = v

    log.debug("_ data_imprint: {}".format(data_imprint))

    set_segment_data_marker(flame_clip_segment, data_imprint)

    return True


def ls():
    """List available containers.
    """
    # TODO: ls
    pass


def parse_container(tl_segment, validate=True):
    """Return container data from timeline_item's openpype tag.
    """
    # TODO: parse_container
    pass


def update_container(tl_segment, data=None):
    """Update container data to input timeline_item's openpype tag.
    """
    # TODO: update_container
    pass

def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle node passthrough states on instance toggles."""

    log.info("instance toggle: {}, old_value: {}, new_value:{} ".format(
        instance, old_value, new_value))

    # from openpype.hosts.resolve import (
    #     set_publish_attribute
    # )

    # # Whether instances should be passthrough based on new value
    # timeline_item = instance.data["item"]
    # set_publish_attribute(timeline_item, new_value)


def remove_instance(instance):
    """Remove instance marker from track item."""
    # TODO: remove_instance
    pass


def list_instances():
    """List all created instances from current workfile."""
    # TODO: list_instances
    pass


def imprint(segment, data=None):
    """
    Adding openpype data to Flame timeline segment.

    Also including publish attribute into tag.

    Arguments:
        segment (flame.PySegment)): flame api object
        data (dict): Any data which needst to be imprinted

    Examples:
        data = {
            'asset': 'sq020sh0280',
            'family': 'render',
            'subset': 'subsetMain'
        }
    """
    data = data or {}

    set_segment_data_marker(segment, data)

    # add publish attribute
    set_publish_attribute(segment, True)


@contextlib.contextmanager
def maintained_selection():
    import flame
    from .lib import CTX

    # check if segment is selected
    if isinstance(CTX.selection[0], flame.PySegment):
        sequence = get_current_sequence(CTX.selection)

        try:
            with maintained_segment_selection(sequence) as selected:
                yield
        finally:
            # reset all selected clips
            reset_segment_selection(sequence)
            # select only original selection of segments
            for segment in selected:
                segment.selected = True
