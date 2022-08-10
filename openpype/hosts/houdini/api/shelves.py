from cProfile import label
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
            "SHELF WARNGING: No custom shelves found in project settings."
        )
        return

    for shelf_set_config in shelves_set_config:
        shelf_set_filepath = shelf_set_config.get('shelf_set_source_path')

        if shelf_set_filepath[current_os]:
            if not os.path.isfile(shelf_set_filepath[current_os]):
                raise FileNotFoundError(
                    "SHELF ERROR: This path doesn't exist - {}".format(
                        shelf_set_filepath[current_os]
                    )
                )

            hou.shelves.newShelfSet(file_path=shelf_set_filepath[current_os])
            continue

        shelf_set_name = shelf_set_config.get('shelf_set_name')
        if not shelf_set_name:
            log.warning(
                "SHELF WARNGING: No name found in shelf set definition."
            )
            return

        shelf_set = get_or_create_shelf_set(shelf_set_name)

        shelves_definition = shelf_set_config.get('shelf_definition')

        if not shelves_definition:
            log.warning(
                "SHELF WARNING: \
No shelf definition found for shelf set named '{}'".format(shelf_set_name)
            )
            return

        for shelf_definition in shelves_definition:
            shelf_name = shelf_definition.get('shelf_name')
            if not shelf_name:
                log.warning(
                    "SHELF WARNGING: No name found in shelf set definition."
                )
                return

            shelf = get_or_create_shelf(shelf_name)

        # go through each tool
        # if filepath exists, load the tool, add it to the shelf and continue
        # create the tool
        # add it to a list of tools

        # add the tools list to the shelf with the tools already in it
        # add the shelf to the shelf set with the shelfs already in it


def get_or_create_shelf_set(shelf_set_label):
    all_shelves_sets = hou.shelves.shelfSets().values()

    shelf_set = [
        shelf for shelf in all_shelves_sets if shelf.label() == shelf_set_label
    ]

    if shelf_set:
        return shelf_set[0]

    shelf_set_name = shelf_set_label.replace(' ', '_').lower()
    new_shelf_set = hou.shelves.newShelfSet(
        name=shelf_set_name,
        label=shelf_set_label
    )
    return new_shelf_set


def get_or_create_shelf(shelf_label):
    all_shelves = hou.shelves.shelves().values()

    shelf = [s for s in all_shelves if s.label() == shelf_label]

    if shelf:
        return shelf[0]

    shelf_name = shelf_label.replace(' ', '_').lower()
    new_shelf = hou.shelves.newShelf(
        name=shelf_name,
        label=shelf_label
    )
    return new_shelf


def get_or_create_tool():
    pass
