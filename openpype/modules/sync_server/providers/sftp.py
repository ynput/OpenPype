import os
import os.path
import time
import threading
import platform

from openpype.api import Logger
from openpype.api import get_system_settings
from .abstract_provider import AbstractProvider
log = Logger().get_logger("SyncServer")

pysftp = None
try:
    import pysftp
    import paramiko
except (ImportError, SyntaxError):
    pass

    # handle imports from Python 2 hosts - in those only basic methods are used
    log.warning("Import failed, imported from Python 2, operations will fail.")


class SFTPHandler(AbstractProvider):
    """
        Implementation of SFTP API.

        Authentication could be done in 2 ways:
            - user and password
            - ssh key file for user (optionally password for ssh key)

        Settings could be overwritten per project.

    """
    CODE = 'sftp'
    LABEL = 'SFTP'

    def __init__(self, project_name, site_name, tree=None, presets=None):
        self.presets = None
        self.project_name = project_name
        self.site_name = site_name
        self.root = None
        self._conn = None

        self.presets = presets
        if not self.presets:
            log.warning("Sync Server: There are no presets for {}.".
                        format(site_name))
            return

        # store to instance for reconnect
        self.sftp_host = presets["sftp_host"]
        self.sftp_port = presets["sftp_port"]
        self.sftp_user = presets["sftp_user"]
        self.sftp_pass = presets["sftp_pass"]
        self.sftp_key = presets["sftp_key"]
        self.sftp_key_pass = presets["sftp_key_pass"]

        self._tree = None

    @property
    def conn(self):
        """SFTP connection, cannot be used in all places though."""
        if not self._conn:
            self._conn = self._get_conn()

        return self._conn

    def is_active(self):
        """
            Returns True if provider is activated, eg. has working credentials.
        Returns:
            (boolean)
        """
        return self.presets["enabled"] and self.conn is not None

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

            Currently not implemented in Settings yet!

            Returns:
                (list) of dict
        """
        # {platform} tells that value is multiplatform and only specific OS
        # should be returned
        editable = [
            # credentials could be overridden on Project or User level
            {
                'key': "sftp_host",
                'label': "SFTP host name",
                'type': 'text'
            },
            {
                "type": "number",
                "key": "sftp_port",
                "label": "SFTP port"
            },
            {
                'key': "sftp_user",
                'label': "SFTP user name",
                'type': 'text'
            },
            {
                'key': "sftp_pass",
                'label': "SFTP password",
                'type': 'text'
            },
            {
                'key': "sftp_key",
                'label': "SFTP user ssh key",
                'type': 'path',
                "multiplatform": True
            },
            {
                'key': "sftp_key_pass",
                'label': "SFTP user ssh key password",
                'type': 'text'
            },
            # roots could be overridden only on Project level, User cannot
            {
                "key": "root",
                "label": "Roots",
                "type": "dict-roots",
                "object_type": {
                    "type": "path",
                    "multiplatform": False,
                    "multipath": False
                }
            }
        ]
        return editable

    @classmethod
    def get_local_settings_schema(cls):
        """
            Returns dict for editable properties on local settings level

            Currently not implemented in Settings yet!

            Returns:
                (dict)
        """
        editable = [
            # credentials could be override on Project or User level
            {
                'key': "sftp_user",
                'label': "SFTP user name",
                'type': 'text'
            },
            {
                'key': "sftp_pass",
                'label': "SFTP password",
                'type': 'text'
            },
            {
                'key': "sftp_key",
                'label': "SFTP user ssh key",
                'type': 'path',
                "multiplatform": True
            },
            {
                'key': "sftp_key_pass",
                'label': "SFTP user ssh key password",
                'type': 'text'
            }
        ]
        return editable

    def get_roots_config(self, anatomy=None):
        """
            Returns root values for path resolving

            Use only Settings as GDrive cannot be modified by Local Settings

        Returns:
            (dict) - {"root": {"root": "/My Drive"}}
                     OR
                     {"root": {"root_ONE": "value", "root_TWO":"value}}
            Format is importing for usage of python's format ** approach
        """
        # roots cannot be locally overridden
        return self.presets['root']

    def get_tree(self):
        """
            Building of the folder tree could be potentially expensive,
            constructor provides argument that could inject previously created
            tree.
            Tree structure must be handled in thread safe fashion!
        Returns:
             (dictionary) - url to id mapping
        """
        # not needed in this provider
        pass

    def create_folder(self, path):
        """
            Create all nonexistent folders and subfolders in 'path'.
            Updates self._tree structure with new paths

        Args:
            path (string): absolute path, starts with GDrive root,
                           without filename
        Returns:
            (string) folder id of lowest subfolder from 'path'
        """
        self.conn.makedirs(path)

        return os.path.basename(path)

    def upload_file(self, source_path, target_path,
                    server, collection, file, representation, site,
                    overwrite=False):
        """
            Uploads single file from 'source_path' to destination 'path'.
            It creates all folders on the path if are not existing.

        Args:
            source_path (string):
            target_path (string): absolute path with or without name of a file
            overwrite (boolean): replace existing file

            arguments for saving progress:
            server (SyncServer): server instance to call update_db on
            collection (str): name of collection
            file (dict): info about uploaded file (matches structure from db)
            representation (dict): complete repre containing 'file'
            site (str): site name

        Returns:
            (string) file_id of created/modified file ,
                throws FileExistsError, FileNotFoundError exceptions
        """
        if not os.path.isfile(source_path):
            raise FileNotFoundError("Source file {} doesn't exist."
                                    .format(source_path))

        if self.file_path_exists(target_path):
            if not overwrite:
                raise ValueError("File {} exists, set overwrite".
                                 format(target_path))

        thread = threading.Thread(target=self._upload,
                                  args=(source_path, target_path))
        thread.start()
        self._mark_progress(collection, file, representation, server,
                            site, source_path, target_path, "upload")

        return os.path.basename(target_path)

    def _upload(self, source_path, target_path):
        print("copying {}->{}".format(source_path, target_path))
        conn = self._get_conn()
        conn.put(source_path, target_path)

    def download_file(self, source_path, target_path,
                      server, collection, file, representation, site,
                      overwrite=False):
        """
            Downloads single file from 'source_path' (remote) to 'target_path'.
            It creates all folders on the local_path if are not existing.
            By default existing file on 'target_path' will trigger an exception

        Args:
            source_path (string): absolute path on provider
            target_path (string): absolute path with or without name of a file
            overwrite (boolean): replace existing file

            arguments for saving progress:
            server (SyncServer): server instance to call update_db on
            collection (str): name of collection
            file (dict): info about uploaded file (matches structure from db)
            representation (dict): complete repre containing 'file'
            site (str): site name

        Returns:
            (string) file_id of created/modified file ,
                throws FileExistsError, FileNotFoundError exceptions
        """
        if not self.file_path_exists(source_path):
            raise FileNotFoundError("Source file {} doesn't exist."
                                    .format(source_path))

        if os.path.isfile(target_path):
            if not overwrite:
                raise ValueError("File {} exists, set overwrite".
                                 format(target_path))

        thread = threading.Thread(target=self._download,
                                  args=(source_path, target_path))
        thread.start()
        self._mark_progress(collection, file, representation, server,
                            site, source_path, target_path, "download")

        return os.path.basename(target_path)

    def _download(self, source_path, target_path):
        print("downloading {}->{}".format(source_path, target_path))
        conn = self._get_conn()
        conn.get(source_path, target_path)

    def delete_file(self, path):
        """
            Deletes file from 'path'. Expects path to specific file.

        Args:
            path: absolute path to particular file

        Returns:
            None
        """
        if not self.file_path_exists(path):
            raise FileNotFoundError("File {} to be deleted doesn't exist."
                                    .format(path))

        self.conn.remove(path)

    def list_folder(self, folder_path):
        """
            List all files and subfolders of particular path non-recursively.

        Args:
            folder_path (string): absolut path on provider
        Returns:
             (list)
        """
        return list(pysftp.path_advance(folder_path))

    def folder_path_exists(self, file_path):
        """
            Checks if path from 'file_path' exists. If so, return its
            folder id.
        Args:
            file_path (string): path with / as a separator
        Returns:
            (string) folder id or False
        """
        if not file_path:
            return False

        return self.conn.isdir(file_path)

    def file_path_exists(self, file_path):
        """
            Checks if 'file_path' exists on GDrive

        Args:
            file_path (string): separated by '/', from root, with file name
        Returns:
            (dictionary|boolean) file metadata | False if not found
        """
        if not file_path:
            return False

        return self.conn.isfile(file_path)

    @classmethod
    def get_presets(cls):
        """
            Get presets for this provider
        Returns:
            (dictionary) of configured sites
        """
        provider_presets = None
        try:
            provider_presets = (
                get_system_settings()["modules"]
                ["sync_server"]
                ["providers"]
                ["sftp"]
            )
        except KeyError:
            log.info(("Sync Server: There are no presets for SFTP " +
                      "provider.").
                     format(str(provider_presets)))
            return
        return provider_presets

    def _get_conn(self):
        """
            Returns fresh sftp connection.

            It seems that connection cannot be cached into self.conn, at least
            for get and put which run in separate threads.

        Returns:
            pysftp.Connection
        """
        if not pysftp:
            raise ImportError

        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None

        conn_params = {
            'host': self.sftp_host,
            'port': self.sftp_port,
            'username': self.sftp_user,
            'cnopts': cnopts
        }
        if self.sftp_pass and self.sftp_pass.strip():
            conn_params['password'] = self.sftp_pass
        if self.sftp_key:  # expects .pem format, not .ppk!
            conn_params['private_key'] = \
                self.sftp_key[platform.system().lower()]
        if self.sftp_key_pass:
            conn_params['private_key_pass'] = self.sftp_key_pass

        try:
            return pysftp.Connection(**conn_params)
        except (paramiko.ssh_exception.SSHException,
                pysftp.exceptions.ConnectionException):
            log.warning("Couldn't connect", exc_info=True)

    def _mark_progress(self, collection, file, representation, server, site,
                       source_path, target_path, direction):
        """
            Updates progress field in DB by values 0-1.

            Compares file sizes of source and target.
        """
        pass
        if direction == "upload":
            source_file_size = os.path.getsize(source_path)
        else:
            source_file_size = self.conn.stat(source_path).st_size

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
                if direction == "upload":
                    target_file_size = self.conn.stat(target_path).st_size
                else:
                    target_file_size = os.path.getsize(target_path)
            except FileNotFoundError:
                pass
            time.sleep(0.5)
