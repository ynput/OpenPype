# -*- coding: utf-8 -*-
import sys
import os
import errno
import re
import uuid
import logging
from contextlib import contextmanager
import json

import six

from openpype.lib import StringTemplate
from openpype.client import get_asset_by_name
from openpype.settings import get_current_project_settings
from openpype.pipeline import get_current_project_name, get_current_asset_name
from openpype.pipeline.context_tools import (
    get_current_context_template_data,
    get_current_project_asset
)
from openpype.widgets import popup
import hou


self = sys.modules[__name__]
self._parent = None
log = logging.getLogger(__name__)
JSON_PREFIX = "JSON:::"


def get_asset_fps(asset_doc=None):
    """Return current asset fps."""

    if asset_doc is None:
        asset_doc = get_current_project_asset(fields=["data.fps"])
    return asset_doc["data"]["fps"]


def set_id(node, unique_id, overwrite=False):
    exists = node.parm("id")
    if not exists:
        imprint(node, {"id": unique_id})

    if not exists and overwrite:
        node.setParm("id", unique_id)


def get_id(node):
    """Get the `cbId` attribute of the given node.

    Args:
        node (hou.Node): the name of the node to retrieve the attribute from

    Returns:
        str: cbId attribute of the node.

    """

    if node is not None:
        return node.parm("id")


def generate_ids(nodes, asset_id=None):
    """Returns new unique ids for the given nodes.

    Note: This does not assign the new ids, it only generates the values.

    To assign new ids using this method:
    >>> nodes = ["a", "b", "c"]
    >>> for node, id in generate_ids(nodes):
    >>>     set_id(node, id)

    To also override any existing values (and assign regenerated ids):
    >>> nodes = ["a", "b", "c"]
    >>> for node, id in generate_ids(nodes):
    >>>     set_id(node, id, overwrite=True)

    Args:
        nodes (list): List of nodes.
        asset_id (str or bson.ObjectId): The database id for the *asset* to
            generate for. When None provided the current asset in the
            active session is used.

    Returns:
        list: A list of (node, id) tuples.

    """

    if asset_id is None:
        project_name = get_current_project_name()
        asset_name = get_current_asset_name()
        # Get the asset ID from the database for the asset of current context
        asset_doc = get_asset_by_name(project_name, asset_name, fields=["_id"])

        assert asset_doc, "No current asset found in Session"
        asset_id = asset_doc['_id']

    node_ids = []
    for node in nodes:
        _, uid = str(uuid.uuid4()).rsplit("-", 1)
        unique_id = "{}:{}".format(asset_id, uid)
        node_ids.append((node, unique_id))

    return node_ids


def get_id_required_nodes():

    valid_types = ["geometry"]
    nodes = {n for n in hou.node("/out").children() if
             n.type().name() in valid_types}

    return list(nodes)


def get_output_parameter(node):
    """Return the render output parameter name of the given node

    Example:
        root = hou.node("/obj")
        my_alembic_node = root.createNode("alembic")
        get_output_parameter(my_alembic_node)
        # Result: "output"

    Args:
        node(hou.Node): node instance

    Returns:
        hou.Parm

    """

    node_type = node.type().name()
    if node_type == "geometry":
        return node.parm("sopoutput")
    elif node_type == "alembic":
        return node.parm("filename")
    elif node_type == "comp":
        return node.parm("copoutput")
    elif node_type == "opengl":
        return node.parm("picture")
    elif node_type == "arnold":
        if node.evalParm("ar_ass_export_enable"):
            return node.parm("ar_ass_file")
    elif node_type == "Redshift_Proxy_Output":
        return node.parm("RS_archive_file")

    raise TypeError("Node type '%s' not supported" % node_type)


def set_scene_fps(fps):
    hou.setFps(fps)


# Valid FPS
def validate_fps():
    """Validate current scene FPS and show pop-up when it is incorrect

    Returns:
        bool

    """

    fps = get_asset_fps()
    current_fps = hou.fps()  # returns float

    if current_fps != fps:

        # Find main window
        parent = hou.ui.mainQtWindow()
        if parent is None:
            pass
        else:
            dialog = popup.PopupUpdateKeys(parent=parent)
            dialog.setModal(True)
            dialog.setWindowTitle("Houdini scene does not match project FPS")
            dialog.setMessage("Scene %i FPS does not match project %i FPS" %
                              (current_fps, fps))
            dialog.setButtonText("Fix")

            # on_show is the Fix button clicked callback
            dialog.on_clicked_state.connect(lambda: set_scene_fps(fps))

            dialog.show()

            return False

    return True


def create_remote_publish_node(force=True):
    """Function to create a remote publish node in /out

    This is a hacked "Shell" node that does *nothing* except for triggering
    `colorbleed.lib.publish_remote()` as pre-render script.

    All default attributes of the Shell node are hidden to the Artist to
    avoid confusion.

    Additionally some custom attributes are added that can be collected
    by a Collector to set specific settings for the publish, e.g. whether
    to separate the jobs per instance or process in one single job.

    """

    cmd = "import colorbleed.lib; colorbleed.lib.publish_remote()"

    existing = hou.node("/out/REMOTE_PUBLISH")
    if existing:
        if force:
            log.warning("Removing existing '/out/REMOTE_PUBLISH' node..")
            existing.destroy()
        else:
            raise RuntimeError("Node already exists /out/REMOTE_PUBLISH. "
                               "Please remove manually or set `force` to "
                               "True.")

    # Create the shell node
    out = hou.node("/out")
    node = out.createNode("shell", node_name="REMOTE_PUBLISH")
    node.moveToGoodPosition()

    # Set color make it stand out (avalon/pyblish color)
    node.setColor(hou.Color(0.439, 0.709, 0.933))

    # Set the pre-render script
    node.setParms({
        "prerender": cmd,
        "lprerender": "python"  # command language
    })

    # Lock the attributes to ensure artists won't easily mess things up.
    node.parm("prerender").lock(True)
    node.parm("lprerender").lock(True)

    # Lock up the actual shell command
    command_parm = node.parm("command")
    command_parm.set("")
    command_parm.lock(True)
    shellexec_parm = node.parm("shellexec")
    shellexec_parm.set(False)
    shellexec_parm.lock(True)

    # Get the node's parm template group so we can customize it
    template = node.parmTemplateGroup()

    # Hide default tabs
    template.hideFolder("Shell", True)
    template.hideFolder("Scripts", True)

    # Hide default settings
    template.hide("execute", True)
    template.hide("renderdialog", True)
    template.hide("trange", True)
    template.hide("f", True)
    template.hide("take", True)

    # Add custom settings to this node.
    parm_folder = hou.FolderParmTemplate("folder", "Submission Settings")

    # Separate Jobs per Instance
    parm = hou.ToggleParmTemplate(name="separateJobPerInstance",
                                  label="Separate Job per Instance",
                                  default_value=False)
    parm_folder.addParmTemplate(parm)

    # Add our custom Submission Settings folder
    template.append(parm_folder)

    # Apply template back to the node
    node.setParmTemplateGroup(template)


def render_rop(ropnode):
    """Render ROP node utility for Publishing.

    This renders a ROP node with the settings we want during Publishing.
    """
    # Print verbose when in batch mode without UI
    verbose = not hou.isUIAvailable()

    # Render
    try:
        ropnode.render(verbose=verbose,
                       # Allow Deadline to capture completion percentage
                       output_progress=verbose)
    except hou.Error as exc:
        # The hou.Error is not inherited from a Python Exception class,
        # so we explicitly capture the houdini error, otherwise pyblish
        # will remain hanging.
        import traceback
        traceback.print_exc()
        raise RuntimeError("Render failed: {0}".format(exc))


def imprint(node, data, update=False):
    """Store attributes with value on a node

    Depending on the type of attribute it creates the correct parameter
    template. Houdini uses a template per type, see the docs for more
    information.

    http://www.sidefx.com/docs/houdini/hom/hou/ParmTemplate.html

    Because of some update glitch where you cannot overwrite existing
    ParmTemplates on node using:
        `setParmTemplates()` and `parmTuplesInFolder()`
    update is done in another pass.

    Args:
        node(hou.Node): node object from Houdini
        data(dict): collection of attributes and their value
        update (bool, optional): flag if imprint should update
            already existing data or leave them untouched and only
            add new.

    Returns:
        None

    """
    if not data:
        return
    if not node:
        self.log.error("Node is not set, calling imprint on invalid data.")
        return

    current_parms = {p.name(): p for p in node.spareParms()}
    update_parms = []
    templates = []

    for key, value in data.items():
        if value is None:
            continue

        parm = get_template_from_value(key, value)

        if key in current_parms:
            if node.evalParm(key) == data[key]:
                continue
            if not update:
                log.debug(f"{key} already exists on {node}")
            else:
                log.debug(f"replacing {key}")
                update_parms.append(parm)
            continue

        templates.append(parm)

    parm_group = node.parmTemplateGroup()
    parm_folder = parm_group.findFolder("Extra")

    # if folder doesn't exist yet, create one and append to it,
    # else append to existing one
    if not parm_folder:
        parm_folder = hou.FolderParmTemplate("folder", "Extra")
        parm_folder.setParmTemplates(templates)
        parm_group.append(parm_folder)
    else:
        for template in templates:
            parm_group.appendToFolder(parm_folder, template)
            # this is needed because the pointer to folder
            # is for some reason lost every call to `appendToFolder()`
            parm_folder = parm_group.findFolder("Extra")

    node.setParmTemplateGroup(parm_group)

    # TODO: Updating is done here, by calling probably deprecated functions.
    #       This needs to be addressed in the future.
    if not update_parms:
        return

    for parm in update_parms:
        node.replaceSpareParmTuple(parm.name(), parm)


def lsattr(attr, value=None, root="/"):
    """Return nodes that have `attr`
     When `value` is not None it will only return nodes matching that value
     for the given attribute.
     Args:
         attr (str): Name of the attribute (hou.Parm)
         value (object, Optional): The value to compare the attribute too.
            When the default None is provided the value check is skipped.
        root (str): The root path in Houdini to search in.
    Returns:
        list: Matching nodes that have attribute with value.
    """
    if value is None:
        # Use allSubChildren() as allNodes() errors on nodes without
        # permission to enter without a means to continue of querying
        # the rest
        nodes = hou.node(root).allSubChildren()
        return [n for n in nodes if n.parm(attr)]
    return lsattrs({attr: value})


def lsattrs(attrs, root="/"):
    """Return nodes matching `key` and `value`
    Arguments:
        attrs (dict): collection of attribute: value
        root (str): The root path in Houdini to search in.
    Example:
        >> lsattrs({"id": "myId"})
        ["myNode"]
        >> lsattr("id")
        ["myNode", "myOtherNode"]
    Returns:
        list: Matching nodes that have attribute with value.
    """

    matches = set()
    # Use allSubChildren() as allNodes() errors on nodes without
    # permission to enter without a means to continue of querying
    # the rest
    nodes = hou.node(root).allSubChildren()
    for node in nodes:
        for attr in attrs:
            if not node.parm(attr):
                continue
            elif node.evalParm(attr) != attrs[attr]:
                continue
            else:
                matches.add(node)

    return list(matches)


def read(node):
    """Read the container data in to a dict

    Args:
        node(hou.Node): Houdini node

    Returns:
        dict

    """
    # `spareParms` returns a tuple of hou.Parm objects
    data = {}
    if not node:
        return data
    for parameter in node.spareParms():
        value = parameter.eval()
        # test if value is json encoded dict
        if isinstance(value, six.string_types) and \
                value.startswith(JSON_PREFIX):
            try:
                value = json.loads(value[len(JSON_PREFIX):])
            except json.JSONDecodeError:
                # not a json
                pass
        data[parameter.name()] = value

    return data


@contextmanager
def maintained_selection():
    """Maintain selection during context
    Example:
        >>> with maintained_selection():
        ...     # Modify selection
        ...     node.setSelected(on=False, clear_all_selected=True)
        >>> # Selection restored
    """

    previous_selection = hou.selectedNodes()
    try:
        yield
    finally:
        # Clear the selection
        # todo: does hou.clearAllSelected() do the same?
        for node in hou.selectedNodes():
            node.setSelected(on=False)

        if previous_selection:
            for node in previous_selection:
                node.setSelected(on=True)


def reset_framerange():
    """Set frame range and FPS to current asset"""

    # Get asset data
    project_name = get_current_project_name()
    asset_name = get_current_asset_name()
    # Get the asset ID from the database for the asset of current context
    asset_doc = get_asset_by_name(project_name, asset_name)
    asset_data = asset_doc["data"]

    # Get FPS
    fps = get_asset_fps(asset_doc)

    # Get Start and End Frames
    frame_start = asset_data.get("frameStart")
    frame_end = asset_data.get("frameEnd")

    if frame_start is None or frame_end is None:
        log.warning("No edit information found for %s" % asset_name)
        return

    handle_start = asset_data.get("handleStart", 0)
    handle_end = asset_data.get("handleEnd", 0)

    frame_start -= int(handle_start)
    frame_end += int(handle_end)

    # Set frame range and FPS
    print("Setting scene FPS to {}".format(int(fps)))
    set_scene_fps(fps)
    hou.playbar.setFrameRange(frame_start, frame_end)
    hou.playbar.setPlaybackRange(frame_start, frame_end)
    hou.setFrame(frame_start)


def get_main_window():
    """Acquire Houdini's main window"""
    if self._parent is None:
        self._parent = hou.ui.mainQtWindow()
    return self._parent


def get_template_from_value(key, value):
    if isinstance(value, float):
        parm = hou.FloatParmTemplate(name=key,
                                     label=key,
                                     num_components=1,
                                     default_value=(value,))
    elif isinstance(value, bool):
        parm = hou.ToggleParmTemplate(name=key,
                                      label=key,
                                      default_value=value)
    elif isinstance(value, int):
        parm = hou.IntParmTemplate(name=key,
                                   label=key,
                                   num_components=1,
                                   default_value=(value,))
    elif isinstance(value, six.string_types):
        parm = hou.StringParmTemplate(name=key,
                                      label=key,
                                      num_components=1,
                                      default_value=(value,))
    elif isinstance(value, (dict, list, tuple)):
        parm = hou.StringParmTemplate(name=key,
                                      label=key,
                                      num_components=1,
                                      default_value=(
                                          JSON_PREFIX + json.dumps(value),))
    else:
        raise TypeError("Unsupported type: %r" % type(value))

    return parm


def get_frame_data(node):
    """Get the frame data: start frame, end frame and steps.

    Args:
        node(hou.Node)

    Returns:
        dict: frame data for star, end and steps.

    """
    data = {}

    if node.parm("trange") is None:

        return data

    if node.evalParm("trange") == 0:
        self.log.debug("trange is 0")
        return data

    data["frameStart"] = node.evalParm("f1")
    data["frameEnd"] = node.evalParm("f2")
    data["steps"] = node.evalParm("f3")

    return data


def splitext(name, allowed_multidot_extensions):
    # type: (str, list) -> tuple
    """Split file name to name and extension.

    Args:
        name (str): File name to split.
        allowed_multidot_extensions (list of str): List of allowed multidot
            extensions.

    Returns:
        tuple: Name and extension.
    """

    for ext in allowed_multidot_extensions:
        if name.endswith(ext):
            return name[:-len(ext)], ext

    return os.path.splitext(name)


def get_top_referenced_parm(parm):

    processed = set()  # disallow infinite loop
    while True:
        if parm.path() in processed:
            raise RuntimeError("Parameter references result in cycle.")

        processed.add(parm.path())

        ref = parm.getReferencedParm()
        if ref.path() == parm.path():
            # It returns itself when it doesn't reference
            # another parameter
            return ref
        else:
            parm = ref


def evalParmNoFrame(node, parm, pad_character="#"):

    parameter = node.parm(parm)
    assert parameter, "Parameter does not exist: %s.%s" % (node, parm)

    # If the parameter has a parameter reference, then get that
    # parameter instead as otherwise `unexpandedString()` fails.
    parameter = get_top_referenced_parm(parameter)

    # Substitute out the frame numbering with padded characters
    try:
        raw = parameter.unexpandedString()
    except hou.Error as exc:
        print("Failed: %s" % parameter)
        raise RuntimeError(exc)

    def replace(match):
        padding = 1
        n = match.group(2)
        if n and int(n):
            padding = int(n)
        return pad_character * padding

    expression = re.sub(r"(\$F([0-9]*))", replace, raw)

    with hou.ScriptEvalContext(parameter):
        return hou.expandStringAtFrame(expression, 0)


def get_color_management_preferences():
    """Get default OCIO preferences"""
    return {
        "config": hou.Color.ocio_configPath(),
        "display": hou.Color.ocio_defaultDisplay(),
        "view": hou.Color.ocio_defaultView()
    }


def get_obj_node_output(obj_node):
    """Find output node.

    If the node has any output node return the
    output node with the minimum `outputidx`.
    When no output is present return the node
    with the display flag set. If no output node is
    detected then None is returned.

    Arguments:
        node (hou.Node): The node to retrieve a single
            the output node for.

    Returns:
        Optional[hou.Node]: The child output node.

    """

    outputs = obj_node.subnetOutputs()
    if not outputs:
        return

    elif len(outputs) == 1:
        return outputs[0]

    else:
        return min(outputs,
                   key=lambda node: node.evalParm('outputidx'))


def get_output_children(output_node, include_sops=True):
    """Recursively return a list of all output nodes
    contained in this node including this node.

    It works in a similar manner to output_node.allNodes().
    """
    out_list = [output_node]

    if output_node.childTypeCategory() == hou.objNodeTypeCategory():
        for child in output_node.children():
            out_list += get_output_children(child, include_sops=include_sops)

    elif include_sops and \
            output_node.childTypeCategory() == hou.sopNodeTypeCategory():
        out = get_obj_node_output(output_node)
        if out:
            out_list += [out]

    return out_list


def get_resolution_from_doc(doc):
    """Get resolution from the given asset document. """

    if not doc or "data" not in doc:
        print("Entered document is not valid. \"{}\"".format(str(doc)))
        return None

    resolution_width = doc["data"].get("resolutionWidth")
    resolution_height = doc["data"].get("resolutionHeight")

    # Make sure both width and height are set
    if resolution_width is None or resolution_height is None:
        print("No resolution information found for \"{}\"".format(doc["name"]))
        return None

    return int(resolution_width), int(resolution_height)


def set_camera_resolution(camera, asset_doc=None):
    """Apply resolution to camera from asset document of the publish"""

    if not asset_doc:
        asset_doc = get_current_project_asset()

    resolution = get_resolution_from_doc(asset_doc)

    if resolution:
        print("Setting camera resolution: {} -> {}x{}".format(
            camera.name(), resolution[0], resolution[1]
        ))
        camera.parm("resx").set(resolution[0])
        camera.parm("resy").set(resolution[1])


def get_camera_from_container(container):
    """Get camera from container node. """

    cameras = container.recursiveGlob(
        "*",
        filter=hou.nodeTypeFilter.ObjCamera,
        include_subnets=False
    )

    assert len(cameras) == 1, "Camera instance must have only one camera"
    return cameras[0]


def get_context_var_changes():
    """get context var changes."""

    houdini_vars_to_update = {}

    project_settings = get_current_project_settings()
    houdini_vars_settings = \
        project_settings["houdini"]["general"]["update_houdini_var_context"]

    if not houdini_vars_settings["enabled"]:
        return houdini_vars_to_update

    houdini_vars = houdini_vars_settings["houdini_vars"]

    # No vars specified - nothing to do
    if not houdini_vars:
        return houdini_vars_to_update

    # Get Template data
    template_data = get_current_context_template_data()

    # Set Houdini Vars
    for item in houdini_vars:
        # For consistency reasons we always force all vars to be uppercase
        item["var"] = item["var"].upper()

        # get and resolve template in value
        item_value = StringTemplate.format_template(
            item["value"],
            template_data
        )

        if item["var"] == "JOB" and item_value == "":
            # sync $JOB to $HIP if $JOB is empty
            item_value = os.environ["HIP"]

        if item["is_directory"]:
            item_value = item_value.replace("\\", "/")

        current_value = hou.hscript("echo -n `${}`".format(item["var"]))[0]

        # sync both environment variables.
        # because houdini doesn't do that by default
        # on opening new files
        os.environ[item["var"]] = current_value

        if current_value != item_value:
            houdini_vars_to_update.update(
                {
                    item["var"]: (
                        current_value, item_value, item["is_directory"]
                    )
                }
            )

    return houdini_vars_to_update


def update_houdini_vars_context():
    """Update asset context variables"""

    for var, (old, new, is_directory) in get_context_var_changes().items():
        if is_directory:
            try:
                os.makedirs(new)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    print(
                        "  - Failed to create ${} dir. Maybe due to "
                        "insufficient permissions.".format(var)
                    )

        hou.hscript("set {}={}".format(var, new))
        os.environ[var] = new
        print("  - Updated ${} to {}".format(var, new))


def update_houdini_vars_context_dialog():
    """Show pop-up to update asset context variables"""
    update_vars = get_context_var_changes()
    if not update_vars:
        # Nothing to change
        return

    message = "\n".join(
        "${}: {} -> {}".format(var, old or "None", new)
        for var, (old, new, is_directory) in update_vars.items()
    )
    parent = hou.ui.mainQtWindow()
    dialog = popup.PopupUpdateKeys(parent=parent)
    dialog.setModal(True)
    dialog.setWindowTitle("Houdini scene has outdated asset variables")
    dialog.setMessage(message)
    dialog.setButtonText("Fix")

    # on_show is the Fix button clicked callback
    dialog.on_clicked_state.connect(lambda: update_houdini_vars_context())

    dialog.show()
