import os

from ayon_api import get_folders_hierarchy
from openpype.settings import get_project_settings
from openpype.hosts.unreal.api.pipeline import (
    generate_sequence,
    set_sequence_hierarchy,
)


def get_default_sequence_path(settings):
    """Get default render folder from blender settings."""

    sequence_path = settings['unreal']['sequence_path']
    if sequence_path.endswith("/"):
        sequence_path = sequence_path.rstrip("/")

    return f"/Game/{sequence_path}"


def _create_sequence(
        element, sequence_path, parent_path="", parent_seq=None,
        parent_fr=None
):
    path = f"{parent_path}/{element['name']}"
    hierarchy_dir = f"{sequence_path}{path}"

    # Create sequence for the current element
    sequence, frame_range = generate_sequence(element["name"], hierarchy_dir)

    # Add the sequence to the parent element if provided
    if parent_seq:
        set_sequence_hierarchy(
            parent_seq, sequence,
            parent_fr[1],
            frame_range[0], frame_range[1],
            [])

    if not element["children"]:
        return

    # Traverse the children and create sequences recursively
    for child in element["children"]:
        _create_sequence(
            child, sequence_path, parent_path=path,
            parent_seq=sequence, parent_fr=frame_range)


def build_sequence_hierarchy():
    """
    Builds the sequence hierarchy by creating sequences from the root element.

    Raises:
        ValueError: If the sequence root element is not found in the hierarchy.
    """
    print("Building sequence hierarchy...")

    project = os.environ.get("AVALON_PROJECT")

    settings = get_project_settings(project)
    sequence_path = get_default_sequence_path(settings)

    sequence_root_name = "shots"

    hierarchy = get_folders_hierarchy(project_name=project)["hierarchy"]

    # Find the sequence root element in the hierarchy
    sequence_root = next((
        element
        for element in hierarchy
        if element["name"] == sequence_root_name
    ), None)

    # Raise an error if the sequence root element is not found
    if not sequence_root:
        raise ValueError(f"Could not find {sequence_root_name} in hierarchy")

    # Start creating sequences from the root element
    _create_sequence(sequence_root, sequence_path)
