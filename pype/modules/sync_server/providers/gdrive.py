from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient import errors
import random
from .abstract_provider import AbstractProvider
# If modifying these scopes, delete the file token.pickle.
from googleapiclient.http import MediaFileUpload
from pype.api import  Logger

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/drive.file']  # for write|delete

log = Logger().get_logger("SyncServer")


class GDriveHandler(AbstractProvider):
    FOLDER_STR = 'application/vnd.google-apps.folder'

    def __init__(self):
        self.service = self._get_gd_service()
        self.root = self.service.files().get(fileId='root').execute()
        self.tree = self._build_tree(self.list_folders())

    def _get_gd_service(self):
        """
            Authorize client with 'credentials.json', stores token into
            'token.pickle'.
            Produces service that communicates with GDrive API.
        :return:
        """
        creds = None
        # The file token.pickle stores the user's access and refresh tokens,
        # and is created automatically when the authorization flow completes
        # for the first time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    os.path.dirname(__file__) + '/credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        service = build('drive', 'v3',
                        credentials=creds, cache_discovery=False)
        return service

    def _build_tree(self, folders):
        """
            Create in-memory structure resolving paths to folder id as recursive
            quering might be slower.
            Initialized in the time of class initialization.
            Maybe should be persisted
            Tree is structure of path to id:
                '/': {'id': '1234567'}
                '/PROJECT_FOLDER': {'id':'222222'}
                '/PROJECT_FOLDER/Assets': {'id': '3434545'}
        :param folders: list of dictionaries with folder metadata
        :return: <dictionary> - path as a key, folder id as a value
        """
        log.debug("build_tree len {}".format(len(folders)))
        tree = {"/": {"id": self.root["id"]}}
        ending_by = {self.root["id"]: "/" + self.root["name"]}
        not_changed_times = 0
        folders_cnt = len(folders) * 5
        # exit loop for weird unresolved folders, raise ValueError, safety
        while folders and not_changed_times < folders_cnt:
            folder = folders.pop(0)
            # weird cases without parents, shared folders, etc,
            # parent under root
            parent = folder.get("parents", [self.root["id"]])[0]

            if folder["id"] == self.root["id"]:  # do not process root
                continue

            if parent in ending_by:
                path_key = ending_by[parent] + "/" + folder["name"]
                ending_by[folder["id"]] = path_key
                tree[path_key] = {"id": folder["id"]}
            else:
                not_changed_times += 1
                if not_changed_times % 10 == 0:  # try to reshuffle deadlocks
                    random.shuffle(folders)
                folders.append(folder)  # dont know parent, wait until shows up

        if len(folders) > 0:
            raise ValueError("Some folders path are not resolved {}"
                             .format(folders))

        return tree

    def get_root_name(self):
        """
            Return name of root folder. Needs to be used as a beginning of
            absolute gdrive path
        :return: <string> - plain name, no '/'
        """
        return self.root["name"]

    def create_folder(self, path):
        """
            Create all nonexistent folders and subfolders in 'path'.
            Updates self.tree structure with new paths

        :param path: absolute path, starts with GDrive root, without filename
        :return: <string> folder id of lowest subfolder from 'path'
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
                    self.tree[new_path_key] = {"id": folder_id}

                    path = new_path_key

                return folder_id

    def upload_file(self, source_path, path, overwrite=False):
        """
            Uploads single file from 'source_path' to destination 'path'.
            It creates all folders on the path if are not existing.

        :param source_path:
        :param path: absolute path with or without name of the file
        :param overwrite: replace existing file
        :return: <string> file_id of created/modified file ,
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
                file = self.service.files().update(fileId=file["id"],
                                                   body=file_metadata,
                                                   media_body=media,
                                                   fields='id').execute()

        except errors.HttpError as ex:
            if ex.resp['status'] == '404':
                return False
            if ex.resp['status'] == '403':
                log.info("Forbidden received, hit quota. Injecting 60s delay.")
                import time
                time.sleep(60)
                return False
            raise

        return file["id"]

    def download_file(self, source_path, local_path):
        pass

    def delete_folder(self, path, force=False):
        """
            Deletes folder on GDrive. Checks if folder contains any files or
            subfolders. In that case raises error, could be overriden by
            'force' argument.
            In that case deletes folder on 'path' and all its children.

        :param path: absolute path on GDrive
        :param force: delete even if children in folder
        :return: None
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
            raise ValueError("Folder {} is not empty, use 'force'".format(path))

        self.service.files().delete(fileId=folder_id).execute()

    def delete_file(self, path):
        """
            Deletes file from 'path'. Expects path to specific file.
        :param path: absolute path to particular file
        :return: None
        """
        file = self.file_path_exists(path)
        if not file:
            raise ValueError("File {} doesn't exist")
        self.service.files().delete(fileId=file["id"]).execute()

    def _get_folder_metadata(self, path):
        """
            Get info about folder with 'path'
        :param path: <string>
        :return: <dictionary> with metadata or raises ValueError
        """
        try:
            return self.tree[path]
        except Exception:
            raise ValueError("Uknown folder id {}".format(id))

    def list_folder(self, folder_path):
        """
            List all files and subfolders of particular path non-recursively.
        :param folder_path: absolut path on provider
        :return: <list>
        """
        pass

    def list_folders(self):
        """ Lists all folders in GDrive.
            Used to build in-memory structure of path to folder ids model.
        :return: list of dictionaries('id', 'name', [parents])
        """
        folders = []
        page_token = None
        fields = 'nextPageToken, files(id, name, parents)'
        while True:
            q = self._handle_q("mimeType='application/vnd.google-apps.folder'")
            response = self.service.files().list(q=q,
                                                 spaces='drive',
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
        :return: list of dictionaries('id', 'name', [parents])
        """
        files = []
        page_token = None
        fields = 'nextPageToken, files(id, name, parents)'
        while True:
            q = self._handle_q("")
            response = self.service.files().list(q=q,
                                                 spaces='drive',
                                                 fields=fields,
                                                 pageToken=page_token).execute()
            files.extend(response.get('files', []))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break

        return files

    def folder_path_exists(self, file_path):
        """
            Checks if path from 'file_path' exists. If so, return its folder id.
        :param file_path: gdrive path with / as a separator
        :return: <string> folder id or False
        """
        if not file_path:
            return False

        root, ext = os.path.splitext(file_path)
        if not ext:
            file_path += '/'

        dir_path = os.path.dirname(file_path)

        path = self.tree.get(dir_path, None)
        if path:
            return path["id"]

        return False

    def file_path_exists(self, file_path):
        """
            Checks if 'file_path' exists on GDrive
        :param file_path: separated by '/', from root, with file name
        :return: file metadata | False if not found
        """
        folder_id = self.folder_path_exists(file_path)
        if folder_id:
            return self.file_exists(os.path.basename(file_path), folder_id)
        return False

    def file_exists(self, file_name, folder_id):
        """
            Checks if 'file_name' exists in 'folder_id'
        :param file_name:
        :param folder_id: google drive folder id
        :return: file metadata, False if not found
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
        :param q: <string> query portion
        :param trashed: False|True
        :return: <string>
        """
        parts = [q]
        if not trashed:
            parts.append(" trashed = false ")

        return " and ".join(parts)

    def _iterfiles(self, name=None, is_folder=None, parent=None,
                   order_by='folder,name,createdTime'):
        """
            Function to list resources in folders, used by _walk
        :param name:
        :param is_folder:
        :param parent:
        :param order_by:
        :return:
        """
        q = []
        if name is not None:
            q.append("name = '%s'" % name.replace("'", "\\'"))
        if is_folder is not None:
            q.append("mimeType %s '%s'" % (
                    '=' if is_folder else '!=', self.FOLDER_STR))
        if parent is not None:
            q.append("'%s' in parents" % parent.replace("'", "\\'"))
        params = {'pageToken': None, 'orderBy': order_by}
        if q:
            params['q'] = ' and '.join(q)
        while True:
            response = self.service.files().list(**params).execute()
            for f in response['files']:
                yield f
            try:
                params['pageToken'] = response['nextPageToken']
            except KeyError:
                return

    def _walk(self, top='root', by_name=False):
        """
            Recurcively walk through folders, could be api requests expensive.
        :param top: <string> folder id to start walking, 'root' is total root
        :param by_name:
        :return: <generator>
        """
        if by_name:
            top, = self._iterfiles(name=top, is_folder=True)
        else:
            top = self.service.files().get(fileId=top).execute()
            if top['mimeType'] != self.FOLDER_STR:
                raise ValueError('not a folder: %r' % top)
        stack = [((top['name'],), top)]
        while stack:
            path, top = stack.pop()
            dirs, files = is_file = [], []
            for f in self._iterfiles(parent=top['id']):
                is_file[f['mimeType'] != self.FOLDER_STR].append(f)
            yield path, top, dirs, files
            if dirs:
                stack.extend((path + (d['name'],), d) for d in reversed(dirs))


if __name__ == '__main__':
    gd = GDriveHandler()
    print(gd.root)
    print(gd.tree)
