"""Functions to parse asset names, versions from file names"""
import os
import re

from openpype.lib import Logger
from openpype.client import get_assets, get_asset_by_name


def get_asset_doc_from_file_name(source_filename, project_name,
                                 version_regex, all_selected_asset_ids=None):
    """Try to parse out asset name from file name provided.

    Artists might provide various file name formats.
    Currently handled:
        - chair.mov
        - chair_v001.mov
        - my_chair_to_upload.mov
    """
    version = None
    asset_name = os.path.splitext(source_filename)[0]
    # Always first check if source filename is directly asset (eg. 'chair.mov')
    matching_asset_doc = get_asset_by_name_case_not_sensitive(
        project_name, asset_name, all_selected_asset_ids)

    if matching_asset_doc is None:
        # name contains also a version
        matching_asset_doc, version = (
            parse_with_version(project_name, asset_name, version_regex,
                               all_selected_asset_ids))

    if matching_asset_doc is None:
        matching_asset_doc = parse_containing(project_name, asset_name,
                                              all_selected_asset_ids)

    return matching_asset_doc, version


def parse_with_version(project_name, asset_name, version_regex,
                       all_selected_asset_ids=None, log=None):
    """Try to parse asset name from a file name containing version too

    Eg. 'chair_v001.mov' >> 'chair', 1
    """
    if not log:
        log = Logger.get_logger(__name__)
    log.debug(
        ("Asset doc by \"{}\" was not found, trying version regex.".
         format(asset_name)))

    matching_asset_doc = version_number = None

    regex_result = version_regex.findall(asset_name)
    if regex_result:
        _asset_name, _version_number = regex_result[0]
        matching_asset_doc = get_asset_by_name_case_not_sensitive(
            project_name, _asset_name,
            all_selected_asset_ids=all_selected_asset_ids)
        if matching_asset_doc:
            version_number = int(_version_number)

    return matching_asset_doc, version_number


def parse_containing(project_name, asset_name, all_selected_asset_ids=None):
    """Look if file name contains any existing asset name"""
    for asset_doc in get_assets(project_name, asset_ids=all_selected_asset_ids,
                                fields=["name"]):
        if asset_doc["name"].lower() in asset_name.lower():
            return get_asset_by_name(project_name, asset_doc["name"])


def get_asset_by_name_case_not_sensitive(project_name, asset_name,
                                         all_selected_asset_ids=None,
                                         log=None):
    """Handle more cases in file names"""
    if not log:
        log = Logger.get_logger(__name__)
    asset_name = re.compile(asset_name, re.IGNORECASE)

    assets = list(get_assets(project_name, asset_ids=all_selected_asset_ids,
                             asset_names=[asset_name]))
    if assets:
        if len(assets) > 1:
            log.warning("Too many records found for {}".format(
                asset_name))
            return

        return assets.pop()
