from __future__ import print_function
import os.path
import shutil
import threading
import time

from openpype.api import Logger
from .abstract_provider import AbstractProvider

log = Logger().get_logger("SyncServer")


class LocalDriveHandler(AbstractProvider):
    """ Handles required operations on mounted disks with OS """
    def is_active(self):
        return True

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

    def get_tree(self):
        return

    def resolve_path(self, path, root_config, anatomy=None):
        if root_config and not root_config.get("root"):
            root_config = {"root": root_config}

        try:
            if not root_config:
                raise KeyError

            path = path.format(**root_config)
        except KeyError:
            try:
                path = anatomy.fill_root(path)
            except KeyError:
                msg = "Error in resolving local root from anatomy"
                log.error(msg)
                raise ValueError(msg)

        return path

    def _copy(self, source_path, target_path):
        print("copying {}->{}".format(source_path, target_path))
        shutil.copy(source_path, target_path)

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
            target_file_size = os.path.getsize(target_path)
            time.sleep(0.5)
