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

# class GobblerHost(TrayPublisherHost):
#     name = "gobbler"

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
@click.option("-d", "--directory",
              required=True,
              help="Directory to gobble")
def go(project_name, directory=None):
    '''Gobble folder and publish everything in it'''
    print("GO!")
    import pyblish.api
    import pyblish.util
    pyblish.api.register_host("standalonepublisher")

    os.environ["AVALON_PROJECT"] = project_name

    # host = GobblerHost()
    # install_host(host)
    # host.install()
    # print(host.name)
    # print(host.get_current_asset_name())

    # host.set_project_name(project_name)
    # print(host.get_context_data())
    # host.
    # data = json.loads(host.get_context_data())
    # print(data)
    assets_list = list(client.get_assets(project_name))
    assets_dict = {asset['name']: asset for asset in assets_list}  # creating a dict {asset_name: asset} for quickly looking up assets by name later.

    directory = _copy_input_to_staging(directory)
    items_to_publish = _parse_directory_contents(directory)

    # MAIN LOOP
    for item in items_to_publish:

        asset = _fuzz_asset(item.basename(), assets_dict)  # fuzzy match asset

        # host.update_context_data()
        asset_name = asset['name']
        extension = item.extension().strip('.')

        # set up repr path
        if item.frameSet():
            print("sequence")
            representation_path = list(item)[0]
        else:
            print("single")
            representation_path = str(item)
        expected_representations = {extension: representation_path}

        family_name = "image"
        task_name = "Concept"
        subset_name = "Input"
        publish_data = {}
        batch_name = str(directory)

        easy_publish.publish_version(project_name,
                        asset_name,
                        task_name,
                        family_name,
                        subset_name,
                        expected_representations,
                        publish_data,
                        batch_name,)


@cli_main.command()
@click.option("-r", "--named_range",
              required=True,
              help="Name of range containing files to collect")
def collect_input(named_range):
    '''Collects input from named_range to cse/in/YYMMDD_uuid directory'''
    import uuid
    from datetime import datetime

    # Get the current date
    current_date = datetime.now()
    # Format it as YYMMDD
    formatted_date = current_date.strftime("%y%m%d")

    destination = f"Y:\WORKS\_openpype\cse\in\{formatted_date}___{uuid.uuid4()}"
    print(f"Destination: {destination}")
    df = _load_data(named_range)
    for row in df.iterrows():
        _copy_files(row, destination)

def _copy_files(row, destination):
    # copies files from row to destination
    import shutil
    print(row)
    shot = row[1]['shot']
    fg = row[1]['foreground']
    bg = row[1]['background']

    # copy fg
    fg_destination = Path(destination)/shot/"fg"
    shutil.copytree(fg, fg_destination)

    # copy bg
    bg_destination = Path(destination)/shot/"bg"
    shutil.copytree(bg, bg_destination)


def _load_data(named_range):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    SPREADSHEET_ID = '18Z-fn_GUGdWTg0-LW1CcS0Bg75Iczu0qu0omH31yO8M'
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    print(">>>>>>>>>>>>", os.getcwd())
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '../openpype/modules/puf_addons/gobbler/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API and consume all 'data'
    sheet = service.spreadsheets()
    all_lines = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                range=named_range).execute()['values']


    print(all_lines)
    column_names = all_lines[0]
    data = all_lines[1:]

    # Create a DataFrame from the list of rows and specify column names
    df = pandas.DataFrame(data, columns=column_names)
    print(df.head())  # data sanity check


    return df
    # values = result.get('values', [])


def _fuzz_asset(item, assets_dict):
    # Find asset in assets that best matches item
    from fuzzywuzzy import fuzz
    from fuzzywuzzy import process

    asset_names = assets_dict.keys()
    best_match, _ = process.extractOne(str(item), asset_names)
    # , scorer=fuzz.token_sort_ratio)

    asset = assets_dict.get(best_match)
    print(f"Matched {item} to {asset['name']}")
    return asset


def _parse_directory_contents(source_directory):
    import fileseq
    file_sequences = set()

    for dirpath, dirnames, filenames in os.walk(source_directory):
        print(dirpath, dirnames)
        # for dir in dirnames:
        #     # full_path = os.path.join(dirpath, filename)
        #     # print(full_path)

        # Check if the file is part of a sequence
        sequence = fileseq.findSequencesOnDisk(dirpath)
        print(sequence)

        if sequence:
            # Append the sequence to the list
            file_sequences = file_sequences | set(sequence)
    return file_sequences


def _copy_input_to_staging(source_directory):
    # copies input directory to temporary staging area
    import uuid
    # temp_dir = tempfile.TemporaryDirectory()

    import shutil
    import platform
    from openpype.pipeline import Anatomy
    a = Anatomy()
    # print(a.keys())
    # print(a.values())
    # print(a.get("roots")["work"][platform.system().lower()])
    root = a.get("roots")["work"][platform.system().lower()]  # get current work directory
    # print(f"Current work root: {root}")
    # Destination directory where you want to copy to
    temp_name = uuid.uuid4()
    destination_directory = f'{root}/temp/{temp_name}'

    try:
        # Copy the source directory and its contents to the destination
        shutil.copytree(source_directory, destination_directory)
        print(f"Directory copied from {source_directory} to {destination_directory} for staging")
        return destination_directory
    except shutil.Error as e:
        raise(e)
    except FileExistsError as e:
        raise(e)
        # print(f"Destination directory already exists. Please specify a different destination.")
    except Exception as e:
        raise(e)
        # print(f"An error occurred: {e}")


def _print_stdout_until_timeout(popen,
                                timeout=None,
                                app_name=None):
    """Print stdout until app close.

    If app remains open for longer than `timeout` then app is terminated.

    """
    time_start = time.time()
    prefix = f"{app_name}: " if app_name else " "
    for line in popen.stdout:
        # Print stdout
        line_str = line.decode("utf-8")
        print(f"{prefix}{line_str}", end='')

        if timeout and time.time() - time_start > timeout:
            popen.terminate()
            raise RuntimeError("Timeout reached")
