import enlighten
import os
import re
import urllib
from urllib.parse import urlparse
import urllib.request
import urllib.error
import itertools
import hashlib
import tarfile
import zipfile


USER_AGENT = "openpype"


class RemoteFileHandler:
    """Download file from url, might be GDrive shareable link"""

    IMPLEMENTED_ZIP_FORMATS = ['zip', 'tar', 'tgz',
                               'tar.gz', 'tar.xz', 'tar.bz2']

    @staticmethod
    def calculate_md5(fpath, chunk_size):
        md5 = hashlib.md5()
        with open(fpath, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                md5.update(chunk)
        return md5.hexdigest()

    @staticmethod
    def check_md5(fpath, md5, **kwargs):
        return md5 == RemoteFileHandler.calculate_md5(fpath, **kwargs)

    @staticmethod
    def check_integrity(fpath, md5=None):
        if not os.path.isfile(fpath):
            return False
        if md5 is None:
            return True
        return RemoteFileHandler.check_md5(fpath, md5)

    @staticmethod
    def download_url(
        url, root, filename=None,
        md5=None, max_redirect_hops=3
    ):
        """Download a file from a url and place it in root.
        Args:
            url (str): URL to download file from
            root (str): Directory to place downloaded file in
            filename (str, optional): Name to save the file under.
                If None, use the basename of the URL
            md5 (str, optional): MD5 checksum of the download.
                If None, do not check
            max_redirect_hops (int, optional): Maximum number of redirect
                hops allowed
        """
        root = os.path.expanduser(root)
        if not filename:
            filename = os.path.basename(url)
        fpath = os.path.join(root, filename)

        os.makedirs(root, exist_ok=True)

        # check if file is already present locally
        if RemoteFileHandler.check_integrity(fpath, md5):
            print('Using downloaded and verified file: ' + fpath)
            return

        # expand redirect chain if needed
        url = RemoteFileHandler._get_redirect_url(url,
                                                  max_hops=max_redirect_hops)

        # check if file is located on Google Drive
        file_id = RemoteFileHandler._get_google_drive_file_id(url)
        if file_id is not None:
            return RemoteFileHandler.download_file_from_google_drive(
                file_id, root, filename, md5)

        # download the file
        try:
            print('Downloading ' + url + ' to ' + fpath)
            RemoteFileHandler._urlretrieve(url, fpath)
        except (urllib.error.URLError, IOError) as e:
            if url[:5] == 'https':
                url = url.replace('https:', 'http:')
                print('Failed download. Trying https -> http instead.'
                      ' Downloading ' + url + ' to ' + fpath)
                RemoteFileHandler._urlretrieve(url, fpath)
            else:
                raise e

        # check integrity of downloaded file
        if not RemoteFileHandler.check_integrity(fpath, md5):
            raise RuntimeError("File not found or corrupted.")

    @staticmethod
    def download_file_from_google_drive(file_id, root,
                                        filename=None,
                                        md5=None):
        """Download a Google Drive file from  and place it in root.
        Args:
            file_id (str): id of file to be downloaded
            root (str): Directory to place downloaded file in
            filename (str, optional): Name to save the file under.
                If None, use the id of the file.
            md5 (str, optional): MD5 checksum of the download.
                If None, do not check
        """
        # Based on https://stackoverflow.com/questions/38511444/python-download-files-from-google-drive-using-url # noqa
        import requests
        url = "https://docs.google.com/uc?export=download"

        root = os.path.expanduser(root)
        if not filename:
            filename = file_id
        fpath = os.path.join(root, filename)

        os.makedirs(root, exist_ok=True)

        if os.path.isfile(fpath) and RemoteFileHandler.check_integrity(fpath,
                                                                       md5):
            print('Using downloaded and verified file: ' + fpath)
        else:
            session = requests.Session()

            response = session.get(url, params={'id': file_id}, stream=True)
            token = RemoteFileHandler._get_confirm_token(response)

            if token:
                params = {'id': file_id, 'confirm': token}
                response = session.get(url, params=params, stream=True)

            response_content_generator = response.iter_content(32768)
            first_chunk = None
            while not first_chunk:  # filter out keep-alive new chunks
                first_chunk = next(response_content_generator)

            if RemoteFileHandler._quota_exceeded(first_chunk):
                msg = (
                    f"The daily quota of the file {filename} is exceeded and "
                    f"it can't be downloaded. This is a limitation of "
                    f"Google Drive and can only be overcome by trying "
                    f"again later."
                )
                raise RuntimeError(msg)

            RemoteFileHandler._save_response_content(
                itertools.chain((first_chunk, ),
                                response_content_generator), fpath)
            response.close()

    @staticmethod
    def unzip(path, destination_path=None):
        if not destination_path:
            destination_path = os.path.dirname(path)

        _, archive_type = os.path.splitext(path)
        archive_type = archive_type.lstrip('.')

        if archive_type in ['zip']:
            print("Unzipping {}->{}".format(path, destination_path))
            zip_file = zipfile.ZipFile(path)
            zip_file.extractall(destination_path)
            zip_file.close()

        elif archive_type in [
            'tar', 'tgz', 'tar.gz', 'tar.xz', 'tar.bz2'
        ]:
            print("Unzipping {}->{}".format(path, destination_path))
            if archive_type == 'tar':
                tar_type = 'r:'
            elif archive_type.endswith('xz'):
                tar_type = 'r:xz'
            elif archive_type.endswith('gz'):
                tar_type = 'r:gz'
            elif archive_type.endswith('bz2'):
                tar_type = 'r:bz2'
            else:
                tar_type = 'r:*'
            try:
                tar_file = tarfile.open(path, tar_type)
            except tarfile.ReadError:
                raise SystemExit("corrupted archive")
            tar_file.extractall(destination_path)
            tar_file.close()

    @staticmethod
    def _urlretrieve(url, filename, chunk_size):
        with open(filename, "wb") as fh:
            with urllib.request.urlopen(
                urllib.request.Request(url,
                                       headers={"User-Agent": USER_AGENT})) \
                    as response:
                for chunk in iter(lambda: response.read(chunk_size), ""):
                    if not chunk:
                        break
                    fh.write(chunk)

    @staticmethod
    def _get_redirect_url(url, max_hops):
        initial_url = url
        headers = {"Method": "HEAD", "User-Agent": USER_AGENT}

        for _ in range(max_hops + 1):
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=headers)) as response:
                if response.url == url or response.url is None:
                    return url

                url = response.url
        else:
            raise RecursionError(
                f"Request to {initial_url} exceeded {max_hops} redirects. "
                f"The last redirect points to {url}."
            )

    @staticmethod
    def _get_confirm_token(response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value

        return None

    @staticmethod
    def _save_response_content(
        response_gen, destination,
    ):
        with open(destination, "wb") as f:
            pbar = enlighten.Counter(
                total=None, desc="Save content", units="%", color="green")
            progress = 0
            for chunk in response_gen:
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    progress += len(chunk)

                pbar.close()

    @staticmethod
    def _quota_exceeded(first_chunk):
        try:
            return "Google Drive - Quota exceeded" in first_chunk.decode()
        except UnicodeDecodeError:
            return False

    @staticmethod
    def _get_google_drive_file_id(url):
        parts = urlparse(url)

        if re.match(r"(drive|docs)[.]google[.]com", parts.netloc) is None:
            return None

        match = re.match(r"/file/d/(?P<id>[^/]*)", parts.path)
        if match is None:
            return None

        return match.group("id")
