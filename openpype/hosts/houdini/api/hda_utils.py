"""Helper functions for load HDA"""

import os
import random

from openpype.pipeline import registered_host, get_representation_path
from openpype.client import get_representation_by_id, get_representations
from openpype.pipeline.context_tools import get_current_project_name

from openpype.pipeline.thumbnail import get_thumbnail_binary
from openpype.client import get_thumbnail_id_from_source, get_thumbnail

from openpype.hosts.houdini.api import lib

import hou


def get_versions(node):

    # Query versions for representation id
    # so we can use it to update the version menu
    # TODO: implement getting versions from current representation id
    result = []
    for version in [1, 2, 3, 4, 5]:
        result.append(version)
        result.append("v{0:03d}".format(version))

    return result


def get_entity_thumbnail(project_name, entity_id, entity_type):
    thumbnail_id = get_thumbnail_id_from_source(project_name, entity_type,
                                                entity_id)
    if not thumbnail_id:
        return
    thumbnail_entity = get_thumbnail(project_name, thumbnail_id, entity_type,
                                     entity_id)
    if not thumbnail_entity:
        return
    return get_thumbnail_binary(thumbnail_entity, thumbnail_entity["type"])


def get_version_thumbnail(project_name, version_id):
    """Return thumbnail binary data from version id"""
    return get_entity_thumbnail(project_name,
                                entity_id=version_id,
                                entity_type="version")


def on_pick_representation(node):
    """Allow the user to pick a product to load"""

    # TODO: Implement actual picker UI instead of using random representation
    project_name = get_current_project_name()
    representations = list(get_representations(
        project_name,
        representation_names=["abc", "usd"],
        fields=["_id"])
    )
    repre = random.choice(representations)
    repre_id = str(repre["_id"])

    node.parm("representation").set(repre_id)
    on_representation_id_change(node)


def update_info(node, representation_doc):
    """Update project, asset, subset, version, representation name parms.

     Arguments:
         node (hou.Node): Node to update
         representation_doc (dict): Representation entity document.

     """
    if representation_doc:
        context = representation_doc["context"]
        project = context["project"]["name"]
        asset = context["asset"]
        subset = context["subset"]
        if "version" in context:
            version = "v{0:03d}".format(context["version"])
        else:
            # TODO: Some contexts don't appear to have version, maybe those are
            #   hero versions?
            version = "<hero>"
        representation = context["representation"]
    else:
        project = "-"
        asset = "-"
        subset = "-"
        version = "-"
        representation = "-"

    node.parm('project_name').set(project)
    node.parm('asset_name').set(asset)
    node.parm('subset_name').set(subset)
    node.parm('version_name').set(version)
    node.parm('representation_name').set(representation)


def _get_thumbnail(project_name, version_id, thumbnail_dir):
    folder = hou.text.expandString(thumbnail_dir)
    path = os.path.join(folder, "{}_thumbnail.jpg".format(version_id))
    expanded_path = hou.text.expandString(path)
    if os.path.isfile(expanded_path):
        return path

    # Try and create a thumbnail cache file
    data = get_version_thumbnail(project_name, version_id)
    if data:
        thumbnail_dir_expanded = hou.text.expandString(thumbnail_dir)
        os.makedirs(thumbnail_dir_expanded, exist_ok=True)
        with open(expanded_path, "wb") as f:
            f.write(data)
        return path


def set_representation(node, repre_id):
    if repre_id:
        host = registered_host()
        context = host.get_current_context()
        project_name = context["project_name"]
        try:
            repre_doc = get_representation_by_id(project_name, repre_id)
        except Exception:
            # Ignore invalid representation ids silently
            repre_doc = None
        update_info(node, repre_doc)

        if repre_doc:
            path = get_representation_path(repre_doc)
            node.parm('file').lock(False)
            node.parm('file').set(path)
            node.parm('file').lock(True)

            if node.evalParm("show_thumbnail"):
                # Update thumbnail
                # TODO: Cache thumbnail path as well
                version_id = repre_doc["parent"]
                thumbnail_dir = node.evalParm("thumbnail_cache_dir")
                thumbnail_path = _get_thumbnail(project_name, version_id,
                                                thumbnail_dir)
                set_node_thumbnail(node, thumbnail_path)
            return

    node.parm('file').lock(False)
    node.parm('file').set("")
    node.parm('file').lock(True)
    set_node_thumbnail(node, None)


def set_node_thumbnail(node, thumbnail):
    """Update node thumbnail to thumbnail"""
    if thumbnail is None:
        lib.set_node_thumbnail(node, None)

    rect = compute_thumbnail_rect(node)
    lib.set_node_thumbnail(node, thumbnail, rect)


def compute_thumbnail_rect(node):
    """Compute thumbnail bounding rect based on thumbnail parms"""
    offset_x = node.evalParm("thumbnail_offsetx")
    offset_y = node.evalParm("thumbnail_offsety")
    width = node.evalParm("thumbnail_size")
    # todo: compute height from aspect of actual
    #   image file.
    aspect = 0.5625  # for now assume 16:9
    height = width * aspect

    center = 0.5
    half_width = (width * .5)

    return hou.BoundingRect(
        offset_x + center - half_width,
        offset_y,
        offset_x + center + half_width,
        offset_y + height
    )


def on_thumbnail_show_changed(node):
    """Callback on thumbnail show parm changed"""
    if node.evalParm("show_thumbnail"):
        # For now, update all
        on_representation_id_change(node)
    else:
        lib.remove_all_thumbnails(node)


def on_thumbnail_size_changed(node):
    """Callback on thumbnail offset or size parms changed"""
    thumbnail = lib.get_node_thumbnail(node)
    if thumbnail:
        rect = compute_thumbnail_rect(node)
        thumbnail.setRect(rect)
        lib.set_node_thumbnail(node, thumbnail)


def on_representation_id_change(node):
    """Callback on representation id changed"""
    repre_id = node.evalParm("representation")
    set_representation(node, repre_id)


def setup_flag_changed_callback(node):
    """Register flag changed callback (for thumbnail brightness)"""
    node.addEventCallback(
        (hou.nodeEventType.FlagChanged,),
        on_flag_changed
    )


def on_flag_changed(node, **kwargs):
    """On node flag changed callback.

    Updates the brightness of attached thumbnails
    """
    # Update node thumbnails brightness with the
    # bypass state of the node.
    parent = node.parent()
    images = lib.get_background_images(parent)
    if not images:
        return

    brightness = 0.3 if node.isBypassed() else 1.0
    has_changes = False
    node_path = node.path()
    for image in images:
        if image.relativeToPath() == node_path:
            image.setBrightness(brightness)
            has_changes = True

    if has_changes:
        lib.set_background_images(parent, images)


def keep_background_images_linked(node, old_name):
    """Reconnect background images to node from old name.

     Used as callback on node name changes to keep thumbnails linked."""
    from openpype.hosts.houdini.api.lib import (
        get_background_images,
        set_background_images
    )

    parent = node.parent()
    images = get_background_images(parent)
    if not images:
        return

    changes = False
    old_path = f"{node.parent().path()}/{old_name}"
    for image in images:
        if image.relativeToPath() == old_path:
            image.setRelativeToPath(node.path())
            changes = True

    if changes:
        set_background_images(parent, images)
