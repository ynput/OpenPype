from __future__ import print_function
import os.path
import shutil
import threading
import time

from openpype.api import Logger, Anatomy
from .abstract_provider import AbstractProvider

log = Logger().get_logger("SyncServer")


class LocalDriveHandler(AbstractProvider):
    CODE = 'local_drive'
    LABEL = 'Local drive'

    """ Handles required operations on mounted disks with OS """
    def __init__(self, project_name, site_name, tree=None, presets=None):
        self.presets = None
        self.active = False
        self.project_name = project_name
        self.site_name = site_name
        self._editable_properties = {}

        self.active = self.is_active()

    def is_active(self):
        return True

    @classmethod
    def get_system_settings_schema(cls):
        """
            Returns dict for editable properties on system settings level


            Returns:
                (list) of dict
        """
        return []

    @classmethod
    def get_project_settings_schema(cls):
        """
            Returns dict for editable properties on project settings level


            Returns:
                (list) of dict
        """
        # for non 'studio' sites, 'studio' is configured in Anatomy
        editable = [
            {
                "key": "root",
                "label": "Roots",
                "type": "dict-roots",
                "object_type": {
                    "type": "path",
                    "multiplatform": True,
                    "multipath": False
                }
            }
        ]
        return editable

    @classmethod
    def get_local_settings_schema(cls):
        """
            Returns dict for editable properties on local settings level


            Returns:
                (dict)
        """
        editable = [
            {
                'key': "root",
                'label': "Roots",
                'type': 'dict'
            }
        ]
        return editable

    def upload_file(self, source_path, target_path,
                    server, collection, file, representation, site,
                    overwrite=False, direction="Upload"):
        """
            Copies file from 'source_path' to 'target_path'
        """
        if not os.path.isfile(source_path):
            raise FileNotFoundError("Source file {} doesn't exist."
                                    .format(source_path))

        if overwrite:
            thread = threading.Thread(target=self._copy,
                                      args=(source_path, target_path))
            thread.start()
            self._mark_progress(collection, file, representation, server,
                                site, source_path, target_path, direction)
        else:
            if os.path.exists(target_path):
                raise ValueError("File {} exists, set overwrite".
                                 format(target_path))

        return os.path.basename(target_path)

    def download_file(self, source_path, local_path,
                      server, collection, file, representation, site,
                      overwrite=False):
        """
            Download a file form 'source_path' to 'local_path'
        """
        return self.upload_file(source_path, local_path,
                                server, collection, file, representation, site,
                                overwrite, direction="Download")

    def delete_file(self, path):
        """
            Deletes a file at 'path'
        """
        if os.path.exists(path):
            os.remove(path)

    def list_folder(self, folder_path):
        """
            Returns list of files and subfolder in a 'folder_path'. Non recurs
        """
        lst = []
        if os.path.isdir(folder_path):
            for (dir_path, dir_names, file_names) in os.walk(folder_path):
                for name in file_names:
                    lst.append(os.path.join(dir_path, name))
                for name in dir_names:
                    lst.append(os.path.join(dir_path, name))

        return lst

    def create_folder(self, folder_path):
        """
            Creates 'folder_path' on local system

            Args:
                folder_path (string): absolute path on local (and mounted) disk

            Returns:
                (string) - sends back folder_path to denote folder(s) was
                    created
        """
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    def get_roots_config(self, anatomy=None):
        """
            Returns root values for path resolving

            Takes value from Anatomy which takes values from Settings
            overridden by Local Settings

        Returns:
            (dict) - {"root": {"root": "/My Drive"}}
                     OR
                     {"root": {"root_ONE": "value", "root_TWO":"value}}
            Format is importing for usage of python's format ** approach
        """
        if not anatomy:
            anatomy = Anatomy(self.project_name,
                              self._normalize_site_name(self.site_name))

        return {'root': anatomy.roots}

    def get_tree(self):
        return

    def get_configurable_items_for_site(self):
        """
            Returns list of items that should be configurable by User

            Returns:
                (list of dict)
                [{key:"root", label:"root", value:"valueFromSettings"}]
        """
        pass

    def _copy(self, source_path, target_path):
        print("copying {}->{}".format(source_path, target_path))
        try:
            shutil.copy(source_path, target_path)
        except shutil.SameFileError:
            print("same files, skipping")

    def _mark_progress(self, collection, file, representation, server, site,
                       source_path, target_path, direction):
        """
            Updates progress field in DB by values 0-1.

            Compares file sizes of source and target.
        """
        source_file_size = os.path.getsize(source_path)
        target_file_size = 0
        last_tick = status_val = None
        while source_file_size != target_file_size:
            if not last_tick or \
                    time.time() - last_tick >= server.LOG_PROGRESS_SEC:
                status_val = target_file_size / source_file_size
                last_tick = time.time()
                log.debug(direction + "ed %d%%." % int(status_val * 100))
                server.update_db(collection=collection,
                                 new_file_id=None,
                                 file=file,
                                 representation=representation,
                                 site=site,
                                 progress=status_val
                                 )
            try:
                target_file_size = os.path.getsize(target_path)
            except FileNotFoundError:
                pass
            time.sleep(0.5)

    def _normalize_site_name(self, site_name):
        """Transform user id to 'local' for Local settings"""
        if site_name != 'studio':
            return 'local'
        return site_name
