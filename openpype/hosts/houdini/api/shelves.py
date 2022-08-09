import os
import logging

from openpype.settings import get_project_settings

log = logging.getLogger(__name__)


def generate_shelves():
    # load configuration of custom menu
    project_settings = get_project_settings(os.getenv("AVALON_PROJECT"))
    shelves_set_config = project_settings["houdini"]["shelves"]

    if not shelves_set_config:
        log.warning("No custom shelves found.")
        return

    # run the shelf generator for Houdini
    for shelf_set in shelves_set_config:
        pass
        # if shelf_set_source_path is not None we load the source path and return

        # if the shelf set name already exists, do nothing, else, create a new one

        # go through each shelf
        # if shelf_file_path exists, load the shelf and return
        # if the shelf name already exists, do nothing, else, create a new one

        # go through each tool
        # if filepath exists, load the tool, add it to the shelf and continue
        # create the tool
        # add it to a list of tools

        # add the tools list to the shelf with the tools already in it
        # add the shelf to the shelf set with the shelfs already in it


def get_or_create_shelf_set():
    pass


def get_or_create_shelf():
    pass


def get_or_create_tool():
    pass
