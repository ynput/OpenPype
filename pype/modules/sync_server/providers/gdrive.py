from __future__ import print_function
import os.path
from googleapiclient.discovery import build
import google.oauth2.service_account as service_account
from googleapiclient import errors
from .abstract_provider import AbstractProvider
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from pype.api import Logger
from pype.lib import timeit

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/drive.file']  # for write|delete

log = Logger().get_logger("SyncServer")


class GDriveHandler(AbstractProvider):
    """
        Implementation of Google Drive API.
        As GD API doesn't have real folder structure, 'tree' in memory
        structure is build in constructor to map folder paths to folder ids,
        which are used in API. Building of this tree might be expensive and
        slow and should be run only when necessary. Currently is set to
        lazy creation, created only after first call when necessary
    """
    FOLDER_STR = 'application/vnd.google-apps.folder'
    CREDENTIALS_FILE_URL = os.path.dirname(__file__) + '/credentials.json'

    def __init__(self, tree=None):
        self.service = self._get_gd_service()
        self.root = self.service.files().get(fileId='root').execute()
        self._tree = tree

    def _get_gd_service(self):
        """
            Authorize client with 'credentials.json', uses service account.
            Service account needs to have target folder shared with.
            Produces service that communicates with GDrive API.

        Returns:
            None
        """
        creds = service_account.Credentials.from_service_account_file(
            self.CREDENTIALS_FILE_URL,
            scopes=SCOPES)
        service = build('drive', 'v3',
                        credentials=creds, cache_discovery=False)
        return service

    @timeit
    def _build_tree(self, folders):
        """
            Create in-memory structure resolving paths to folder id as
            recursive querying might be slower.
            Initialized in the time of class initialization.
            Maybe should be persisted
            Tree is structure of path to id:
                '/': {'id': '1234567'}
                '/PROJECT_FOLDER': {'id':'222222'}
                '/PROJECT_FOLDER/Assets': {'id': '3434545'}
        Args:
            folders (list): list of dictionaries with folder metadata
        Returns:
            (dictionary) path as a key, folder id as a value
        """
        log.debug("build_tree len {}".format(len(folders)))
        tree = {"/": {"id": self.root["id"]}}
        ending_by = {self.root["id"]: "/" + self.root["name"]}
        no_parents_yet = {}
        while folders:
            folder = folders.pop(0)
            parents = folder.get("parents", [])
            # weird cases, shared folders, etc, parent under root
            if not parents:
                parent = self.root["id"]
            else:
                parent = parents[0]

            if folder["id"] == self.root["id"]:  # do not process root
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

        if len(no_parents_yet) > 0:
            raise ValueError("Some folders path are not resolved {}"
                             .format(no_parents_yet))

        return tree

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

    def get_root_name(self):
        """
            Return name of root folder. Needs to be used as a beginning of
            absolute gdrive path
        Returns:
            (string) - plain name, no '/'
        """
        return self.root["name"]

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

            folder_id = self.folder_path_exists(path)  # lowest common path
            if folder_id:
                while folders_to_create:
                    new_folder_name = folders_to_create.pop()
                    folder_metadata = {
                        'name': new_folder_name,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [folder_id]
                    }
                    folder = self.service.files().create(body=folder_metadata,
                                                         fields='id').execute()
                    folder_id = folder["id"]

                    new_path_key = path + '/' + new_folder_name
                    self.get_tree()[new_path_key] = {"id": folder_id}

                    path = new_path_key

                return folder_id

    def upload_file(self, source_path, path, overwrite=False):
        """
            Uploads single file from 'source_path' to destination 'path'.
            It creates all folders on the path if are not existing.

        Args:
            source_path (string):
            path (string): absolute path with or without name of the file
            overwrite (boolean): replace existing file

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

        file = self.file_path_exists(path + "/" + target_name)
        if file and not overwrite:
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
                                resumable=True)
        try:
            if not file:
                # update doesnt like parent
                file_metadata['parents'] = [folder_id]

                file = self.service.files().create(body=file_metadata,
                                                   media_body=media,
                                                   fields='id').execute()

            else:
                log.debug("update file {}".format(file["id"]))
                file = self.service.files().update(fileId=file["id"],
                                                   body=file_metadata,
                                                   media_body=media,
                                                   fields='id').execute()

        except errors.HttpError as ex:
            if ex.resp['status'] == '404':
                return False
            if ex.resp['status'] == '403':
                # real permission issue
                if 'has not granted' in ex._get_reason().strip():
                    raise PermissionError(ex._get_reason().strip())

                log.warning("Forbidden received, hit quota. "
                            "Injecting 60s delay.")
                import time
                time.sleep(60)
                return False
            raise

        return file["id"]

    def download_file(self, source_path, local_path, overwrite=False):
        """
            Downloads single file from 'source_path' (remote) to 'local_path'.
            It creates all folders on the local_path if are not existing.
            By default existing file on 'local_path' will trigger an exception

        Args:
            source_path (string): absolute path on provider
            local_path (string): absolute path with or without name of the file
            overwrite (boolean): replace existing file

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

        file = os.path.isfile(local_path + "/" + target_name)

        if file and not overwrite:
            raise FileExistsError("File already exists, "
                                  "use 'overwrite' argument")

        request = self.service.files().get_media(fileId=remote_file["id"])

        with open(local_path + "/" + target_name, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()

        return target_name

    def delete_folder(self, path, force=False):
        """
            Deletes folder on GDrive. Checks if folder contains any files or
            subfolders. In that case raises error, could be overriden by
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
            spaces='drive',
            pageSize='1',
            fields=fields).execute()
        children = response.get('files', [])
        if children and not force:
            raise ValueError("Folder {} is not empty, use 'force'".
                             format(path))

        self.service.files().delete(fileId=folder_id).execute()

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
        self.service.files().delete(fileId=file["id"]).execute()

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

    def list_folder(self, folder_path):
        """
            List all files and subfolders of particular path non-recursively.

        Args:
            folder_path (string): absolut path on provider
        Returns:
             (list)
        """
        pass

    @timeit
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
            response = self.service.files().list(q=q,
                                                 pageSize=1000,
                                                 spaces='drive',
                                                 fields=fields,
                                                 pageToken=page_token)\
                .execute()
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
            response = self.service.files().list(q=q,
                                                 spaces='drive',
                                                 fields=fields,
                                                 pageToken=page_token).\
                execute()
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
            spaces='drive',
            fields='nextPageToken, files(id, name, parents, '
                   'mimeType, modifiedTime,size,md5Checksum)').execute()
        if len(response.get('files')) > 1:
            raise ValueError("Too many files returned for {} in {}"
                             .format(file_name, folder_id))

        file = response.get('files', [])
        if not file:
            return False
        return file[0]

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
    gd = GDriveHandler()
    print(gd.root)
    print(gd.get_tree())
