from collections import defaultdict
import shutil
import os

from openpype.client import get_project, get_asset_by_id
from openpype.settings import get_system_settings, get_project_settings
from openpype.pipeline import Anatomy, registered_host
from openpype.pipeline.template_data import get_template_data
from openpype.pipeline.workfile import get_workdir_with_workdir_data
from openpype.tools.push_to_project.app import show

from .utils import bake_gizmos_recursively

import nuke


def bake_container(container):
    """Bake containers to read nodes."""

    node = container["node"]

    # Fetch knobs to remove in order.
    knobs_to_remove = []
    remove = False
    for count in range(0, node.numKnobs()):
        knob = node.knob(count)

        # All knobs from "OpenPype" tab knob onwards.
        if knob.name() == "OpenPype":
            remove = True

        if remove:
            knobs_to_remove.append(knob)

        # Dont remove knobs from "containerId" onwards.
        if knob.name() == "containerId":
            remove = False

    # Knobs needs to be remove in reverse order, because child knobs needs to
    # be remove first.
    for knob in reversed(knobs_to_remove):
        node.removeKnob(knob)

    node["tile_color"].setValue(0)


def main():
    context = show("", "", False, True)

    if context is None:
        return

    # Get workfile path to save to.
    project_name = context["project_name"]
    project_doc = get_project(project_name)
    asset_doc = get_asset_by_id(project_name, context["asset_id"])
    task_name = context["task_name"]
    host = registered_host()
    system_settings = get_system_settings()
    project_settings = get_project_settings(project_name)
    anatomy = Anatomy(project_name)

    workdir_data = get_template_data(
        project_doc, asset_doc, task_name, host.name, system_settings
    )

    workdir = get_workdir_with_workdir_data(
        workdir_data,
        project_name,
        anatomy,
        project_settings=project_settings
    )

    # Save current workfile.
    current_file = host.current_file()
    host.save_file(current_file)

    for container in host.ls():
        bake_container(container)

    # Bake gizmos.
    bake_gizmos_recursively()

    # Copy all read node files to "resources" folder next to workfile and
    # change file path.
    first_frame = int(nuke.root()["first_frame"].value())
    last_frame = int(nuke.root()["last_frame"].value())
    files_by_node_name = defaultdict(set)
    nodes_by_name = {}
    for count in range(first_frame, last_frame + 1):
        nuke.frame(count)
        for node in nuke.allNodes(filter="Read"):
            files_by_node_name[node.name()].add(
                nuke.filename(node, nuke.REPLACE)
            )
            nodes_by_name[node.name()] = node

    resources_dir = os.path.join(workdir, "resources")
    for name, files in files_by_node_name.items():
        dir = os.path.join(resources_dir, name)
        if not os.path.exists(dir):
            os.makedirs(dir)

        for f in files:
            shutil.copy(f, os.path.join(dir, os.path.basename(f)))

        node = nodes_by_name[name]
        path = node["file"].value().replace(os.path.dirname(f), dir)
        node["file"].setValue(path.replace("\\", "/"))

    # Save current workfile to new context.
    basename = os.path.basename(current_file)
    host.save_file(os.path.join(workdir, basename))

    # Open current contex workfile.
    host.open_file(current_file)
