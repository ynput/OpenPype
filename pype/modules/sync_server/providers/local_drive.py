from __future__ import print_function
import os.path
import shutil

from pype.api import Logger
from .abstract_provider import AbstractProvider

log = Logger().get_logger("SyncServer")


class LocalDriveHandler(AbstractProvider):
    """ Handles required operations on mounted disks with OS """
    def is_active(self):
        return True

    def upload_file(self, source_path, target_path, overwrite=True):
        """
            Copies file from 'source_path' to 'target_path'
        """
        if os.path.exists(source_path):
            if overwrite:
                shutil.copy(source_path, target_path)
            else:
                if os.path.exists(target_path):
                    raise ValueError("File {} exists, set overwrite".
                                     format(target_path))

    def download_file(self, source_path, local_path, overwrite=True):
        """
            Download a file form 'source_path' to 'local_path'
        """
        if os.path.exists(source_path):
            if overwrite:
                shutil.copy(source_path, local_path)
            else:
                if os.path.exists(local_path):
                    raise ValueError("File {} exists, set overwrite".
                                     format(local_path))

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
