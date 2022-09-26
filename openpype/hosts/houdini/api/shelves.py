import os
import logging
import platform
import six

from openpype.settings import get_project_settings

import hou

log = logging.getLogger("openpype.hosts.houdini.shelves")

if six.PY2:
    FileNotFoundError = IOError


def generate_shelves():
    """This function generates complete shelves from shelf set to tools
    in Houdini from openpype project settings houdini shelf definition.

    Raises:
        FileNotFoundError: Raised when the shelf set filepath does not exist
    """
    current_os = platform.system().lower()

    # load configuration of houdini shelves
    project_settings = get_project_settings(os.getenv("AVALON_PROJECT"))
    shelves_set_config = project_settings["houdini"]["shelves"]

    if not shelves_set_config:
        log.debug(
            "No custom shelves found in project settings."
        )
        return

    for shelf_set_config in shelves_set_config:
        shelf_set_filepath = shelf_set_config.get('shelf_set_source_path')

        if shelf_set_filepath[current_os]:
            if not os.path.isfile(shelf_set_filepath[current_os]):
                raise FileNotFoundError(
                    "This path doesn't exist - {}".format(
                        shelf_set_filepath[current_os]
                    )
                )

            hou.shelves.newShelfSet(file_path=shelf_set_filepath[current_os])
            continue

        shelf_set_name = shelf_set_config.get('shelf_set_name')
        if not shelf_set_name:
            log.warning(
                "No name found in shelf set definition."
            )
            continue

        shelves_definition = shelf_set_config.get('shelf_definition')
        if not shelves_definition:
            log.debug(
                "No shelf definition found for shelf set named '{}'".format(
                    shelf_set_name
                )
            )
            continue

        shelf_set = get_or_create_shelf_set(shelf_set_name)
        for shelf_definition in shelves_definition:
            shelf_name = shelf_definition.get('shelf_name')
            if not shelf_name:
                log.warning(
                    "No name found in shelf definition."
                )
                continue

            shelf = get_or_create_shelf(shelf_name)

            if not shelf_definition.get('tools_list'):
                log.debug(
                    "No tool definition found for shelf named {}".format(
                        shelf_name
                    )
                )
                continue

            mandatory_attributes = {'name', 'script'}
            for tool_definition in shelf_definition.get('tools_list'):
                # We verify that the name and script attibutes of the tool
                # are set
                if not all(
                    tool_definition[key] for key in mandatory_attributes
                ):
                    log.warning(
                        "You need to specify at least the name and \
the script path of the tool.")
                    continue

                tool = get_or_create_tool(tool_definition, shelf)

                if not tool:
                    continue

                # Add the tool to the shelf if not already in it
                if tool not in shelf.tools():
                    shelf.setTools(list(shelf.tools()) + [tool])

            # Add the shelf in the shelf set if not already in it
            if shelf not in shelf_set.shelves():
                shelf_set.setShelves(shelf_set.shelves() + (shelf,))


def get_or_create_shelf_set(shelf_set_label):
    """This function verifies if the shelf set label exists. If not,
    creates a new shelf set.

    Arguments:
        shelf_set_label (str): The label of the shelf set

    Returns:
        hou.ShelfSet: The shelf set existing or the new one
    """
    all_shelves_sets = hou.shelves.shelfSets().values()

    shelf_set = next((shelf for shelf in all_shelves_sets if
                      shelf.label() == shelf_set_label), None)
    if shelf_set:
        return shelf_set[0]

    shelf_set_name = shelf_set_label.replace(' ', '_').lower()
    new_shelf_set = hou.shelves.newShelfSet(
        name=shelf_set_name,
        label=shelf_set_label
    )
    return new_shelf_set


def get_or_create_shelf(shelf_label):
    """This function verifies if the shelf label exists. If not, creates
    a new shelf.

    Arguments:
        shelf_label (str): The label of the shelf

    Returns:
        hou.Shelf: The shelf existing or the new one
    """
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


def get_or_create_tool(tool_definition, shelf):
    """This function verifies if the tool exists and updates it. If not, creates
    a new one.

    Arguments:
        tool_definition (dict): Dict with label, script, icon and help
        shelf (hou.Shelf): The parent shelf of the tool

    Returns:
        hou.Tool: The tool updated or the new one
    """
    existing_tools = shelf.tools()
    tool_label = tool_definition.get('label')

    existing_tool = [
        tool for tool in existing_tools if tool.label() == tool_label
    ]

    if existing_tool:
        tool_definition.pop('name', None)
        tool_definition.pop('label', None)
        existing_tool[0].setData(**tool_definition)
        return existing_tool[0]

    tool_name = tool_label.replace(' ', '_').lower()

    if not os.path.exists(tool_definition['script']):
        log.warning(
            "This path doesn't exist - {}".format(
                tool_definition['script']
            )
        )
        return

    with open(tool_definition['script']) as f:
        script = f.read()
        tool_definition.update({'script': script})

    new_tool = hou.shelves.newTool(name=tool_name, **tool_definition)

    return new_tool
