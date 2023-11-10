import os
import re
import logging
import platform

from openpype.settings import get_project_settings
from openpype.pipeline import get_current_project_name

from openpype.lib import StringTemplate

import hou

from .lib import get_current_context_template_data_with_asset_data

log = logging.getLogger("openpype.hosts.houdini.shelves")


def generate_shelves():
    """This function generates complete shelves from shelf set to tools
    in Houdini from openpype project settings houdini shelf definition.
    """
    current_os = platform.system().lower()

    # load configuration of houdini shelves
    project_name = get_current_project_name()
    project_settings = get_project_settings(project_name)
    shelves_configs = project_settings["houdini"]["shelves"]

    if not shelves_configs:
        log.debug("No custom shelves found in project settings.")
        return

    # Get Template data
    template_data = get_current_context_template_data_with_asset_data()

    for config in shelves_configs:
        selected_option = config["options"]
        shelf_set_config = config[selected_option]

        shelf_set_filepath = shelf_set_config.get('shelf_set_source_path')
        if shelf_set_filepath:
            shelf_set_os_filepath = shelf_set_filepath[current_os]
            if shelf_set_os_filepath:
                shelf_set_os_filepath = get_path_using_template_data(
                    shelf_set_os_filepath, template_data
                )
                if not os.path.isfile(shelf_set_os_filepath):
                    log.error("Shelf path doesn't exist - "
                              "{}".format(shelf_set_os_filepath))
                    continue

                hou.shelves.loadFile(shelf_set_os_filepath)
                continue

        shelf_set_name = shelf_set_config.get('shelf_set_name')
        if not shelf_set_name:
            log.warning("No name found in shelf set definition.")
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
                log.warning("No name found in shelf definition.")
                continue

            shelf = get_or_create_shelf(shelf_name)

            if not shelf_definition.get('tools_list'):
                log.debug(
                    "No tool definition found for shelf named {}".format(
                        shelf_name
                    )
                )
                continue

            mandatory_attributes = {'label', 'script'}
            for tool_definition in shelf_definition.get('tools_list'):
                # We verify that the name and script attributes of the tool
                # are set
                if not all(
                    tool_definition[key] for key in mandatory_attributes
                ):
                    log.warning(
                        "You need to specify at least the name and the "
                        "script path of the tool.")
                    continue

                tool = get_or_create_tool(
                    tool_definition, shelf, template_data
                )

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
        return shelf_set

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

    shelf = next((s for s in all_shelves if s.label() == shelf_label), None)
    if shelf:
        return shelf

    shelf_name = shelf_label.replace(' ', '_').lower()
    new_shelf = hou.shelves.newShelf(
        name=shelf_name,
        label=shelf_label
    )
    return new_shelf


def get_or_create_tool(tool_definition, shelf, template_data):
    """This function verifies if the tool exists and updates it. If not, creates
    a new one.

    Arguments:
        tool_definition (dict): Dict with label, script, icon and help
        shelf (hou.Shelf): The parent shelf of the tool

    Returns:
        hou.Tool: The tool updated or the new one
    """

    tool_label = tool_definition.get("label")
    if not tool_label:
        log.warning("Skipped shelf without label")
        return

    script_path = tool_definition["script"]
    script_path = get_path_using_template_data(script_path, template_data)
    if not script_path or not os.path.exists(script_path):
        log.warning("This path doesn't exist - {}".format(script_path))
        return

    icon_path = tool_definition["icon"]
    if icon_path:
        icon_path = get_path_using_template_data(icon_path, template_data)
        tool_definition["icon"] = icon_path

    existing_tools = shelf.tools()
    existing_tool = next(
        (tool for tool in existing_tools if tool.label() == tool_label),
        None
    )

    with open(script_path) as stream:
        script = stream.read()

    tool_definition["script"] = script

    if existing_tool:
        tool_definition.pop("label", None)
        existing_tool.setData(**tool_definition)
        return existing_tool

    tool_name = re.sub(r"[^\w\d]+", "_", tool_label).lower()
    return hou.shelves.newTool(name=tool_name, **tool_definition)


def get_path_using_template_data(path, template_data):
    path = StringTemplate.format_template(path, template_data)
    path = path.replace("\\", "/")

    return path
