"""Launch scripts module."""
import os
import time
import pyblish
import click
from pathlib import Path
# import gazu

from openpype.modules import OpenPypeModule
from openpype.pipeline.create import CreateContext
# from abstract_publish import publish_version
from openpype.client import get_project, get_asset_by_name
import openpype.client as client
from openpype.pipeline.context_tools import change_current_context

from . import easy_publish

from openpype.hosts.traypublisher.api import TrayPublisherHost
from openpype.pipeline import install_host
from openpype.lib import Logger

# google spreadsheet
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials # this is deprecated
# from google.auth.credentials import Credentials # but using the new one requires refactoring so not using it for now

import pandas
import pprint

log = Logger.get_logger("Gobbler")

# TODO: ADD GOOGLE PANDAS AND FUZZYWUZZY TO REQUIREMENTS

class GobblerModule(OpenPypeModule):
    label = "Gobble mess from client"
    name = "gobbler"

    def initialize(self, modules_settings):
        self.enabled = True

    def cli(self, click_group):
        click_group.add_command(cli_main)

    def get_global_environments(self):
        """Get addon global environments.

        Use standalone publisher for asset publishing
        """
        return {}
        #     "AVALON_APP_NAME": "standalonepublisher",
        #     "AVALON_APP": "standalonepublisher",
        # }


@click.group(GobblerModule.name,
             help="Ingest mess from client.")
def cli_main():
    pass


@cli_main.command()
@click.option("-p", "--project_name",
              required=True,
              envvar="AVALON_PROJECT",
              help="Project name")
@click.option("-i", "--input_dir",
              required=True,
              help="Directory to gobble")
def gobble(project_name, input_dir):
    '''Gobble folder and publish everything in it'''
    log.info(f"Will gobble {input_dir} to project {project_name}.")
    import pyblish.api
    import pyblish.util
    from datetime import datetime
    pyblish.api.register_host("standalonepublisher")

    os.environ["AVALON_PROJECT"] = project_name
    current_datetime = datetime.now().strftime("%y%m%d%H%M%S") # Format the date and time as YYMMDDHHMMSS

    batch_name = f"Ingest: {os.path.basename(input_dir)}_{current_datetime}"

    assets_and_shots_dict, shots_dict, assets_dict = _project_cache(project_name)

    # create a dict {asset_name: asset} for quickly looking up assets by name later.
    # assuming asset names are unique - which is not an OP requirement but a studio requirement.
    # OP only requires unique hierarchy I believe?

    # copy input to staging directory
    directory = _copy_input_to_staging(input_dir)
    # # alternatively, work on input directory, without staging dir
    # directory = input_dir

    # create png from psd
    # _create_png_from_psd(directory)


    # walk directory and find items to publish
    items_to_publish = _find_sources(directory)

    # MAIN LOOP
    for item in items_to_publish:
        # fuzzy match asset
        file_seq = item[2]
        representations = item[1]
        # search_term = search_term.replace(directory + "\\", "")
        # search_term = item[0]
        search_term = os.path.relpath(item[0], start=directory)
        item_name = os.path.basename(item[0])

        log.info(f"Repr: {representations.keys()}")
        # PRODUCTION LOGIC
        if 'psd' in representations.keys(): # asset!
            log.info(f"asset!")
            asset = _fuzz_asset(search_term, assets_dict)
            log.info(asset['name'])
            is_shot = False
        else:
            asset = _fuzz_asset(search_term, shots_dict)
            is_shot = True
        asset_name = asset['name']

        if is_shot:
            family_name = "render"
            task_name = "Animation"
            if file_seq:
                subset_name = file_seq.basename()
            else:
                subset_name = "renderAnimationMain"

        else:
            family_name = "image"
            task_name = "Concept"
            subset_name = "imageTexture"


        publish_data = {
            "families": ["review"],
        }
        log.info(f"{representations}")
        easy_publish.publish_version(project_name,
                                     asset_name,
                                     task_name,
                                     family_name,
                                     subset_name,
                                     representations,
                                     publish_data,
                                     batch_name,)

    # TODO: clean up staging directory


@cli_main.command()
@click.option("-r", "--named_range",
              required=True,
              help="Name of range containing files to collect")
# TODO: This could be a env var in OP
@click.option("-d", "--directory",
              required=True,
              help="Root directory IN",
              default="Y:\\WORKS\\_openpype\\cse\\in\\")
@click.option("-s", "--spreadsheet",
              required=False,
              help="Id of the spreadsheet",
              default='18Z-fn_GUGdWTg0-LW1CcS0Bg75Iczu0qu0omH31yO8M')
def collect_input(named_range, directory, spreadsheet):
    '''Collects input from named_range to cse/in/YYMMDD_uuid directory'''
    import uuid
    from datetime import datetime

    # Get the current date
    current_date = datetime.now()
    # Format it as YYMMDD
    formatted_date = current_date.strftime("%y%m%d")

    destination = f"{directory}\\{formatted_date}___{uuid.uuid4()}"
    log.info(f"Destination: {destination}")
    df = _load_data(spreadsheet, named_range)
    for row in df.iterrows():
        _copy_files(row, destination)


def _project_cache(project_name):
    # build a few dicts to look up shots and assets quickly
    all_list = list(client.get_assets(project_name))
    all_dict = {asset['name']: asset for asset in all_list}


    shots_dict = {}
    assets_dict = {}
    assets_and_shots_dict = {}
    for asset_name, asset in all_dict.items():
        # this filters out folders and maybe other non-zou elements
        if asset.get('data').get('zou'):
            if asset.get('data').get('zou').get('type') == 'Shot':
                shots_dict[asset_name] = asset
                assets_and_shots_dict[asset_name] = asset
            if asset.get('data').get('zou').get('type') == 'Asset':
                assets_dict[asset_name] = asset
                assets_and_shots_dict[asset_name] = asset
    return assets_and_shots_dict, shots_dict, assets_dict


# def _create_png_from_psd(directory):
#     # walk directory and create png from psd where missing
#     import imageio
#     for root, dirs, files in os.walk(directory):
#         for file in files:
#             if os.path(file)

def _copy_files(row, destination):
    # copies files from row to destination
    import shutil
    log.info(row)
    shot = row[1]['shot']
    fg = row[1]['foreground']
    bg = row[1]['background']

    # copy fg
    fg_destination = Path(destination)/shot/"fg"
    os.makedirs(fg_destination, exist_ok=True)
    if os.path.isfile(fg):
        log.info(f"{fg} is a file.")
        shutil.copy(fg, fg_destination)
    elif os.path.isdir(fg):
        _copymerge_dir(fg, fg_destination)

    # copy bg
    bg_destination = Path(destination)/shot/"bg"
    os.makedirs(bg_destination, exist_ok=True)
    if os.path.isfile(bg):
        log.info(f"{bg} is a file.")
        shutil.copy(bg, bg_destination)
    elif os.path.isdir(bg):
        _copymerge_dir(bg, bg_destination)


def _copymerge_dir(source_directory, destination_directory):
    '''copy/merge directories'''
    import shutil
    if os.path.exists(destination_directory):
        # The destination directory exists; merge the contents.
        for root, dirs, files in os.walk(source_directory):
            for file in files:
                source_path = os.path.join(root, file)
                relative_path = os.path.relpath(source_path, source_directory)
                destination_path = os.path.join(destination_directory, relative_path)

                # Ensure the destination directory exists for the file to be copied.
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)

                # Copy the file from the source to the destination.
                shutil.copy2(source_path, destination_path)
    else:
        # The destination directory doesn't exist; simply copy the source directory.
        shutil.copytree(source_directory, destination_directory)
        log.info(f"Directory '{source_directory}' copied to '{destination_directory}'.")


def _load_data(spreadsheet, named_range):
    """Gets values from a sample spreadsheet.
    """
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    CREDENTIALS_FILE = os.environ.get("OP_HS_GDRIVE_CREDENTIAL")
    creds = None

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(CREDENTIALS_FILE):
        creds = Credentials.from_authorized_user_file(CREDENTIALS_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(CREDENTIALS_FILE, 'w') as token:
            token.write(creds.to_json())

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API and consume all data
    sheet = service.spreadsheets()
    all_lines = sheet.values().get(
        spreadsheetId=spreadsheet,
        range=named_range
    ).execute()['values']

    column_names = all_lines[0]
    data = all_lines[1:]

    # Create a DataFrame from the list of rows and specify column names
    df = pandas.DataFrame(data, columns=column_names)

    return df


def _fuzz_asset(item, assets_dict):
    # Find asset in assets that best matches item
    from fuzzywuzzy import fuzz
    from fuzzywuzzy import process

    asset_names = assets_dict.keys()
    best_match, _ = process.extractOne(str(item), asset_names)

    asset = assets_dict.get(best_match)
    log.info(f">>> Matched {item} to {asset['name']}")
    return asset


def _find_sources(source_directory):
    import fileseq
    results = list()

    for dirpath, dirnames, filenames in os.walk(source_directory):
        # Check if the file is part of a sequence
        dir_contents = fileseq.findSequencesOnDisk(dirpath)
        # log.info(sequence)

        if dir_contents: # dir not empty
            representations_found = {}
            # log.info(f"Found {len(dir_contents)} items in {dirpath}")
            for item in dir_contents:
                # Append the sequence to the list
                extension = item.extension().strip('.')

                if item.frameSet():  # if sequence
                    # if item.frameSet().start() != item.frameSet().end():  # and not single-frame sequence
                    #     representation_path = item.frame(item.start())
                    #     log.info(f"sequence {representation_path}")
                    # else:  # single-frame sequence, so single frame really
                    #     representation_path = item.frame(item.start())
                    #     log.info(f"single-frame seq: {representation_path}")
                    representation_path = item.frame(item.start())
                    log.info(f"sequence: {representation_path}")
                else:  # single
                    representation_path = str(item)
                    log.info(f"single file - no seq: {representation_path}")
                representations_found[extension] = representation_path
            # log.info(f"Repr found: {representations_found}")
            publish_item = (representation_path, representations_found, item or None)
            results.append(publish_item)
    # log.info(f"Results: {results}")

    return results


def _copy_input_to_staging(source_directory):
    # copies input directory to temporary staging area
    import uuid
    import shutil
    import platform
    from openpype.pipeline import Anatomy
    a = Anatomy()
    root = a.get("roots")["work"][platform.system().lower()]  # get current work directory

    # Destination directory where you want to copy to
    temp_name = os.path.basename(source_directory)+"_"+str(uuid.uuid4())
    destination_directory = f'{root}/temp/{temp_name}'

    try:
        # Copy the source directory and its contents to the destination
        log.info(f"Copying {source_directory} to staging: {destination_directory}")
        shutil.copytree(source_directory, destination_directory)
        log.info(f"Successfully copied from {source_directory} to {destination_directory} for staging")
        return destination_directory
    except shutil.Error as e:
        raise(e)
    except FileExistsError as e:
        raise(e)
        # log.info(f"Destination directory already exists. Please specify a different destination.")
    except Exception as e:
        raise(e)
        # log.info(f"An error occurred: {e}")
