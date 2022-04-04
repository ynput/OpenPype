from __future__ import print_function
import os.path
import time
import sys
import six
import platform

from openpype.api import Logger
from openpype.api import get_system_settings
from .abstract_provider import AbstractProvider
from ..utils import time_function, ResumableError

log = Logger().get_logger("SyncServer")

try:
    from googleapiclient.discovery import build
    import google.oauth2.service_account as service_account
    from googleapiclient import errors
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
except (ImportError, SyntaxError):
    if six.PY3:
        six.reraise(*sys.exc_info())

    # handle imports from Python 2 hosts - in those only basic methods are used
    log.warning("Import failed, imported from Python 2, operations will fail.")

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/drive.readonly']  # for write|delete


class GDriveHandler(AbstractProvider):
    """
        Implementation of Google Drive API.
        As GD API doesn't have real folder structure, 'tree' in memory
        structure is build in constructor to map folder paths to folder ids,
        which are used in API. Building of this tree might be expensive and
        slow and should be run only when necessary. Currently is set to
        lazy creation, created only after first call when necessary.

        Configuration for provider is in
            'settings/defaults/project_settings/global.json'

        Settings could be overwritten per project.

        Example of config:
          "gdrive": {   - site name
            "provider": "gdrive", - type of provider, label must be registered
            "credentials_url": "/my_secret_folder/credentials.json",
            "root": {  - could be "root": "/My Drive" for single root
                "root_one": "/My Drive",
                "root_two": "/My Drive/different_folder"
            }
          }
    """
    CODE = 'gdrive'
    LABEL = 'Google Drive'

    FOLDER_STR = 'application/vnd.google-apps.folder'
    MY_DRIVE_STR = 'My Drive'  # name of root folder of regular Google drive
    CHUNK_SIZE = 2097152  # must be divisible by 256! used for upload chunks

    def __init__(self, project_name, site_name, tree=None, presets=None):
        self.active = False
        self.project_name = project_name
        self.site_name = site_name
        self.service = None
        self.root = None

        self.presets = presets
        if not self.presets:
            log.info("Sync Server: There are no presets for {}.".
                     format(site_name))
            return

        current_platform = platform.system().lower()
        cred_path = self.presets.get("credentials_url", {}). \
            get(current_platform) or ''

        if not cred_path:
            msg = "Sync Server: Please, fill the credentials for gdrive "\
                  "provider for platform '{}' !".format(current_platform)
            log.info(msg)
            return

        try:
            cred_path = cred_path.format(**os.environ)
        except KeyError as e:
            log.info("Sync Server: The key(s) {} does not exist in the "
                     "environment variables".format(" ".join(e.args)))
            return

        if not os.path.exists(cred_path):
            msg = "Sync Server: No credentials for gdrive provider " + \
                  "for '{}' on path '{}'!".format(site_name, cred_path)
            log.info(msg)
            return

        self.service = None
        if self.presets["enabled"]:
            self.service = self._get_gd_service(cred_path)

            self._tree = tree
            self.active = True

    def is_active(self):
        """
            Returns True if provider is activated, eg. has working credentials.
        Returns:
            (boolean)
        """
        return self.presets["enabled"] and self.service is not None

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
        # {platform} tells that value is multiplatform and only specific OS
        # should be returned
        editable = [
            # credentials could be overridden on Project or User level
            {
                "type": "path",
                "key": "credentials_url",
                "label": "Credentials url",
                "multiplatform": True,
                "placeholder": "Credentials url"
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


            Returns:
                (dict)
        """
        editable = [
            # credentials could be override on Project or User level
            {
                'key': "credentials_url",
                'label': "Credentials url",
                'type': 'text',
                'namespace': '{project_settings}/global/sync_server/sites/{site}/credentials_url/{platform}'  # noqa: E501
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
        # GDrive roots cannot be locally overridden
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
        if not self._tree:
            self._tree = self._build_tree(self.list_folders())
        return self._tree

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
        folder_id = self.folder_path_exists(path)
        if folder_id:
            return folder_id
        parts = path.split('/')
        folders_to_create = []

        while parts:
            folders_to_create.append(parts.pop())
            path = '/'.join(parts)
            path = path.strip()
            folder_id = self.folder_path_exists(path)  # lowest common path
            if folder_id:
                while folders_to_create:
                    new_folder_name = folders_to_create.pop()
                    folder_metadata = {
                        'name': new_folder_name,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [folder_id]
                    }
                    folder = self.service.files().create(
                        body=folder_metadata,
                        supportsAllDrives=True,
                        fields='id').execute()
                    folder_id = folder["id"]

                    new_path_key = path + '/' + new_folder_name
                    self.get_tree()[new_path_key] = {"id": folder_id}

                    path = new_path_key
                return folder_id

    def upload_file(self, source_path, path,
                    server, collection, file, representation, site,
                    overwrite=False):
        """
            Uploads single file from 'source_path' to destination 'path'.
            It creates all folders on the path if are not existing.

        Args:
            source_path (string):
            path (string): absolute path with or without name of the file
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

        root, ext = os.path.splitext(path)
        if ext:
            # full path
            target_name = os.path.basename(path)
            path = os.path.dirname(path)
        else:
            target_name = os.path.basename(source_path)
        target_file = self.file_path_exists(path + "/" + target_name)
        if target_file and not overwrite:
            raise FileExistsError("File already exists, "
                                  "use 'overwrite' argument")

        folder_id = self.folder_path_exists(path)
        if not folder_id:
            raise NotADirectoryError("Folder {} doesn't exists".format(path))

        file_metadata = {
            'name': target_name
        }
        media = MediaFileUpload(source_path,
                                mimetype='application/octet-stream',
                                chunksize=self.CHUNK_SIZE,
                                resumable=True)

        try:
            if not target_file:
                # update doesnt like parent
                file_metadata['parents'] = [folder_id]

                request = self.service.files().create(body=file_metadata,
                                                      supportsAllDrives=True,
                                                      media_body=media,
                                                      fields='id')
            else:
                request = self.service.files().update(fileId=target_file["id"],
                                                      body=file_metadata,
                                                      supportsAllDrives=True,
                                                      media_body=media,
                                                      fields='id')

            media.stream()
            log.debug("Start Upload! {}".format(source_path))
            last_tick = status = response = None
            status_val = 0
            while response is None:
                if server.is_representation_paused(representation['_id'],
                                                   check_parents=True,
                                                   project_name=collection):
                    raise ValueError("Paused during process, please redo.")
                if status:
                    status_val = float(status.progress())
                if not last_tick or \
                        time.time() - last_tick >= server.LOG_PROGRESS_SEC:
                    last_tick = time.time()
                    log.debug("Uploaded %d%%." %
                              int(status_val * 100))
                    server.update_db(collection=collection,
                                     new_file_id=None,
                                     file=file,
                                     representation=representation,
                                     site=site,
                                     progress=status_val
                                     )
                status, response = request.next_chunk()

        except errors.HttpError as ex:
            if ex.resp['status'] == '404':
                return False
            if ex.resp['status'] == '403':
                # real permission issue
                if 'has not granted' in ex._get_reason().strip():
                    raise PermissionError(ex._get_reason().strip())

                log.warning("Forbidden received, hit quota. "
                            "Injecting 60s delay.")
                time.sleep(60)
                return False
            raise
        return response['id']

    def download_file(self, source_path, local_path,
                      server, collection, file, representation, site,
                      overwrite=False):
        """
            Downloads single file from 'source_path' (remote) to 'local_path'.
            It creates all folders on the local_path if are not existing.
            By default existing file on 'local_path' will trigger an exception

        Args:
            source_path (string): absolute path on provider
            local_path (string): absolute path with or without name of the file
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
        remote_file = self.file_path_exists(source_path)
        if not remote_file:
            raise FileNotFoundError("Source file {} doesn't exist."
                                    .format(source_path))

        root, ext = os.path.splitext(local_path)
        if ext:
            # full path with file name
            target_name = os.path.basename(local_path)
            local_path = os.path.dirname(local_path)
        else:  # just folder, get file name from source
            target_name = os.path.basename(source_path)

        local_file = os.path.isfile(local_path + "/" + target_name)

        if local_file and not overwrite:
            raise FileExistsError("File already exists, "
                                  "use 'overwrite' argument")

        request = self.service.files().get_media(fileId=remote_file["id"],
                                                 supportsAllDrives=True)

        with open(local_path + "/" + target_name, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            last_tick = status = response = None
            status_val = 0
            while response is None:
                if server.is_representation_paused(representation['_id'],
                                                   check_parents=True,
                                                   project_name=collection):
                    raise ValueError("Paused during process, please redo.")
                if status:
                    status_val = float(status.progress())
                if not last_tick or \
                        time.time() - last_tick >= server.LOG_PROGRESS_SEC:
                    last_tick = time.time()
                    log.debug("Downloaded %d%%." %
                              int(status_val * 100))
                    server.update_db(collection=collection,
                                     new_file_id=None,
                                     file=file,
                                     representation=representation,
                                     site=site,
                                     progress=status_val
                                     )
                status, response = downloader.next_chunk()

        return target_name

    def delete_folder(self, path, force=False):
        """
            Deletes folder on GDrive. Checks if folder contains any files or
            subfolders. In that case raises error, could be overridden by
            'force' argument.
            In that case deletes folder on 'path' and all its children.

        Args:
            path (string): absolute path on GDrive
            force (boolean): delete even if children in folder

        Returns:
            None
        """
        folder_id = self.folder_path_exists(path)
        if not folder_id:
            raise ValueError("Not valid folder path {}".format(path))

        fields = 'nextPageToken, files(id, name, parents)'
        q = self._handle_q("'{}' in parents ".format(folder_id))
        response = self.service.files().list(
            q=q,
            corpora="allDrives",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            pageSize='1',
            fields=fields).execute()
        children = response.get('files', [])
        if children and not force:
            raise ValueError("Folder {} is not empty, use 'force'".
                             format(path))

        self.service.files().delete(fileId=folder_id,
                                    supportsAllDrives=True).execute()

    def delete_file(self, path):
        """
            Deletes file from 'path'. Expects path to specific file.

        Args:
            path: absolute path to particular file

        Returns:
            None
        """
        file = self.file_path_exists(path)
        if not file:
            raise ValueError("File {} doesn't exist")
        self.service.files().delete(fileId=file["id"],
                                    supportsAllDrives=True).execute()

    def list_folder(self, folder_path):
        """
            List all files and subfolders of particular path non-recursively.

        Args:
            folder_path (string): absolut path on provider
        Returns:
             (list)
        """
        pass

    @time_function
    def list_folders(self):
        """ Lists all folders in GDrive.
            Used to build in-memory structure of path to folder ids model.

        Returns:
            (list) of dictionaries('id', 'name', [parents])
        """
        folders = []
        page_token = None
        fields = 'nextPageToken, files(id, name, parents)'
        while True:
            q = self._handle_q("mimeType='application/vnd.google-apps.folder'")
            response = self.service.files().list(
                q=q,
                pageSize=1000,
                corpora="allDrives",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                fields=fields,
                pageToken=page_token).execute()
            folders.extend(response.get('files', []))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break

        return folders

    def list_files(self):
        """ Lists all files in GDrive
            Runs loop through possibly multiple pages. Result could be large,
            if it would be a problem, change it to generator
        Returns:
            (list) of dictionaries('id', 'name', [parents])
        """
        files = []
        page_token = None
        fields = 'nextPageToken, files(id, name, parents)'
        while True:
            q = self._handle_q("")
            response = self.service.files().list(
                q=q,
                corpora="allDrives",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                fields=fields,
                pageToken=page_token).execute()
            files.extend(response.get('files', []))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break

        return files

    def folder_path_exists(self, file_path):
        """
            Checks if path from 'file_path' exists. If so, return its
            folder id.
        Args:
            file_path (string): gdrive path with / as a separator
        Returns:
            (string) folder id or False
        """
        if not file_path:
            return False

        root, ext = os.path.splitext(file_path)
        if not ext:
            file_path += '/'

        dir_path = os.path.dirname(file_path)

        path = self.get_tree().get(dir_path, None)
        if path:
            return path["id"]

        return False

    def file_path_exists(self, file_path):
        """
            Checks if 'file_path' exists on GDrive

        Args:
            file_path (string): separated by '/', from root, with file name
        Returns:
            (dictionary|boolean) file metadata | False if not found
        """
        folder_id = self.folder_path_exists(file_path)
        if folder_id:
            return self.file_exists(os.path.basename(file_path), folder_id)
        return False

    def file_exists(self, file_name, folder_id):
        """
            Checks if 'file_name' exists in 'folder_id'

        Args:
            file_name (string):
            folder_id (int): google drive folder id

        Returns:
            (dictionary|boolean) file metadata, False if not found
        """
        q = self._handle_q("name = '{}' and '{}' in parents"
                           .format(file_name, folder_id))
        response = self.service.files().list(
            q=q,
            corpora="allDrives",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            fields='nextPageToken, files(id, name, parents, '
                   'mimeType, modifiedTime,size,md5Checksum)').execute()
        if len(response.get('files')) > 1:
            raise ValueError("Too many files returned for {} in {}"
                             .format(file_name, folder_id))

        file = response.get('files', [])
        if not file:
            return False
        return file[0]

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
                ["gdrive"]
            )
        except KeyError:
            log.info(("Sync Server: There are no presets for Gdrive " +
                      "provider.").
                     format(str(provider_presets)))
            return
        return provider_presets

    def _get_gd_service(self, credentials_path):
        """
            Authorize client with 'credentials.json', uses service account.
            Service account needs to have target folder shared with.
            Produces service that communicates with GDrive API.

        Returns:
            None
        """
        service = None
        try:
            creds = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=SCOPES)
            service = build('drive', 'v3',
                            credentials=creds, cache_discovery=False)
        except Exception:
            log.error("Connection failed, " +
                      "check '{}' credentials file".format(credentials_path),
                      exc_info=True)

        return service

    def _prepare_root_info(self):
        """
            Prepare info about roots and theirs folder ids from 'presets'.
            Configuration might be for single or multiroot projects.
            Regular My Drive and Shared drives are implemented, their root
            folder ids need to be queried in slightly different way.

        Returns:
            (dicts) of dicts where root folders are keys
            throws ResumableError in case of errors.HttpError
        """
        roots = {}
        config_roots = self.get_roots_config()
        try:
            for path in config_roots.values():
                if self.MY_DRIVE_STR in path:
                    roots[self.MY_DRIVE_STR] = self.service.files()\
                                                   .get(fileId='root')\
                                                   .execute()
                else:
                    shared_drives = []
                    page_token = None

                    while True:
                        response = self.service.drives().list(
                            pageSize=100,
                            pageToken=page_token).execute()
                        shared_drives.extend(response.get('drives', []))
                        page_token = response.get('nextPageToken', None)
                        if page_token is None:
                            break

                    folders = path.split('/')
                    if len(folders) < 2:
                        raise ValueError("Wrong root folder definition {}".
                                         format(path))

                    for shared_drive in shared_drives:
                        if folders[1] in shared_drive["name"]:
                            roots[shared_drive["name"]] = {
                                "name": shared_drive["name"],
                                "id": shared_drive["id"]}
            if self.MY_DRIVE_STR not in roots:  # add My Drive always
                roots[self.MY_DRIVE_STR] = self.service.files() \
                    .get(fileId='root').execute()
        except errors.HttpError:
            log.warning("HttpError in sync loop, "
                        "trying next loop",
                        exc_info=True)
            raise ResumableError

        return roots

    @time_function
    def _build_tree(self, folders):
        """
            Create in-memory structure resolving paths to folder id as
            recursive querying might be slower.
            Initialized in the time of class initialization.
            Maybe should be persisted
            Tree is structure of path to id:
                '/ROOT': {'id': '1234567'}
                '/ROOT/PROJECT_FOLDER': {'id':'222222'}
                '/ROOT/PROJECT_FOLDER/Assets': {'id': '3434545'}
        Args:
            folders (list): list of dictionaries with folder metadata
        Returns:
            (dictionary) path as a key, folder id as a value
        """
        log.debug("build_tree len {}".format(len(folders)))
        if not self.root:  # build only when necessary, could be expensive
            self.root = self._prepare_root_info()

        root_ids = []
        default_root_id = None
        tree = {}
        ending_by = {}
        for root_name, root in self.root.items():  # might be multiple roots
            if root["id"] not in root_ids:
                tree["/" + root_name] = {"id": root["id"]}
                ending_by[root["id"]] = "/" + root_name
                root_ids.append(root["id"])

                if self.MY_DRIVE_STR == root_name:
                    default_root_id = root["id"]

        no_parents_yet = {}
        while folders:
            folder = folders.pop(0)
            parents = folder.get("parents", [])
            # weird cases, shared folders, etc, parent under root
            if not parents:
                parent = default_root_id
            else:
                parent = parents[0]

            if folder["id"] in root_ids:  # do not process root
                continue

            if parent in ending_by:
                path_key = ending_by[parent] + "/" + folder["name"]
                ending_by[folder["id"]] = path_key
                tree[path_key] = {"id": folder["id"]}
            else:
                no_parents_yet.setdefault(parent, []).append((folder["id"],
                                                              folder["name"]))
        loop_cnt = 0
        # break if looped more then X times - safety against infinite loop
        while no_parents_yet and loop_cnt < 20:

            keys = list(no_parents_yet.keys())
            for parent in keys:
                if parent in ending_by.keys():
                    subfolders = no_parents_yet.pop(parent)
                    for folder_id, folder_name in subfolders:
                        path_key = ending_by[parent] + "/" + folder_name
                        ending_by[folder_id] = path_key
                        tree[path_key] = {"id": folder_id}
            loop_cnt += 1

        if len(no_parents_yet) > 0:
            log.debug("Some folders path are not resolved {}".
                      format(no_parents_yet))
            log.debug("Remove deleted folders from trash.")

        return tree

    def _get_folder_metadata(self, path):
        """
            Get info about folder with 'path'
        Args:
            path (string):

        Returns:
         (dictionary) with metadata or raises ValueError
        """
        try:
            return self.get_tree()[path]
        except Exception:
            raise ValueError("Uknown folder id {}".format(id))

    def _handle_q(self, q, trashed=False):
        """ API list call contain trashed and hidden files/folder by default.
            Usually we dont want those, must be included in query explicitly.

        Args:
            q (string): query portion
            trashed (boolean): False|True

        Returns:
            (string) - modified query
        """
        parts = [q]
        if not trashed:
            parts.append(" trashed = false ")

        return " and ".join(parts)


if __name__ == '__main__':
    gd = GDriveHandler('gdrive')
    print(gd.root)
    print(gd.get_tree())
