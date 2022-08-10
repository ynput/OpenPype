import os
import logging
import platform

from openpype.settings import get_project_settings

import hou

log = logging.getLogger("openpype.hosts.houdini")


def generate_shelves():
    current_os = platform.system().lower()
    # load configuration of custom menu
    project_settings = get_project_settings(os.getenv("AVALON_PROJECT"))
    shelves_set_config = project_settings["houdini"]["shelves"]

    if not shelves_set_config:
        log.warning(
            "SHELF ERROR: No custom shelves found in project settings."
        )
        return

    for shelf_set_config in shelves_set_config:
        shelf_set_filepath = shelf_set_config.get('shelf_set_source_path')

        # if shelf_set_source_path is not None we load the source path and continue
        if shelf_set_filepath[current_os]:
            if not os.path.isfile(shelf_set_filepath[current_os]):
                raise FileNotFoundError(
                    "SHELF ERROR: This path doesn't exist - {}".format(
                        shelf_set_filepath[current_os]
                    )
                )

            hou.shelves.newShelfSet(file_path=shelf_set_filepath[current_os])
            continue

        # if the shelf set name already exists, do nothing, else, create a new one
        shelf_set_name = shelf_set_config.get('shelf_set_name')
        shelf_set = get_or_create_shelf_set(shelf_set_name)

        # go through each shelf
        # if shelf_file_path exists, load the shelf and return
        # if the shelf name already exists, do nothing, else, create a new one

        # go through each tool
        # if filepath exists, load the tool, add it to the shelf and continue
        # create the tool
        # add it to a list of tools

        # add the tools list to the shelf with the tools already in it
        # add the shelf to the shelf set with the shelfs already in it


def get_or_create_shelf_set(shelf_set_label):
    all_shelves = hou.shelves.shelfSets().values()

    shelf_set = [
        shelf for shelf in all_shelves if shelf.label() == shelf_set_label
    ]

    if shelf_set:
        return shelf_set[0]

    shelf_set_name = shelf_set_label.replace(' ', '_').lower()
    new_shelf_set = hou.shelves.newShelfSet(
        name=shelf_set_name,
        label=shelf_set_label
    )
    return new_shelf_set


def get_or_create_shelf():
    pass


def get_or_create_tool():
    pass
