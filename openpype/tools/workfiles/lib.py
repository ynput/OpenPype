import os
import shutil
import uuid
import time
import json
import logging
import contextlib

import appdirs


class TempPublishFilesItem(object):
    """Object representing on subfolder in app temp files.

    Args:
        item_id (str): Id of item used as subfolder.
        data (dict): Metadata about temp files.
        directory (str): Path to directory where files are copied to.
    """

    def __init__(self, item_id, data, directory):
        self._id = item_id
        self._directory = directory
        self._filepath = os.path.join(directory, data["filename"])

    @property
    def directory(self):
        return self._directory

    @property
    def filepath(self):
        return self._filepath

    @property
    def id(self):
        return self._id

    @property
    def size(self):
        if os.path.exists(self.filepath):
            s = os.stat(self.filepath)
            return s.st_size
        return 0


class TempPublishFiles(object):
    """Directory where """
    minute_in_seconds = 60
    hour_in_seconds = 60 * minute_in_seconds
    day_in_seconds = 24 * hour_in_seconds

    def __init__(self):
        root_dir = appdirs.user_data_dir(
            "published_workfiles_temp", "openpype"
        )
        if not os.path.exists(root_dir):
            os.makedirs(root_dir)

        metadata_path = os.path.join(root_dir, "metadata.json")
        lock_path = os.path.join(root_dir, "lock.json")

        self._root_dir = root_dir
        self._metadata_path = metadata_path
        self._lock_path = lock_path
        self._log = None

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    @property
    def life_time(self):
        return int(self.hour_in_seconds)

    @property
    def size(self):
        size = 0
        for item in self.get_items():
            size += item.size
        return size

    def add_file(self, src_path):
        filename = os.path.basename(src_path)

        item_id = str(uuid.uuid4())
        dst_dirpath = os.path.join(self._root_dir, item_id)
        if not os.path.exists(dst_dirpath):
            os.makedirs(dst_dirpath)

        dst_path = os.path.join(dst_dirpath, filename)
        shutil.copy(src_path, dst_path)

        now = time.time()
        item_data = {
            "filename": filename,
            "expiration": now + self.life_time,
            "created": now
        }
        with self._modify_data() as data:
            data[item_id] = item_data

        return TempPublishFilesItem(item_id, item_data, dst_dirpath)

    @contextlib.contextmanager
    def _modify_data(self):
        start_time = time.time()
        timeout = 3
        while os.path.exists(self._lock_path):
            time.sleep(0.01)
            if start_time > timeout:
                self.log.warning((
                    "Waited for {} seconds to free lock file. Overriding lock."
                ).format(timeout))

        with open(self._lock_path, "w") as stream:
            json.dump({"pid": os.getpid()}, stream)

        try:
            data = self._get_data()
            yield data
            with open(self._metadata_path, "w") as stream:
                json.dump(data, stream)

        finally:
            os.remove(self._lock_path)

    def _get_data(self):
        output = {}
        if not os.path.exists(self._metadata_path):
            return output

        try:
            with open(self._metadata_path, "r") as stream:
                output = json.load(stream)
        except Exception:
            self.log.warning("Failed to read metadata file.", exc_info=True)
        return output

    def cleanup(self, check_expiration=True):
        data = self._get_data()
        now = time.time()
        remove_ids = set()
        for item_id, item_data in data.items():
            if check_expiration and now < item_data["expiration"]:
                continue

            remove_ids.add(item_id)

        for item_id in remove_ids:
            try:
                self.remove_id(item_id)
            except Exception:
                self.log.warning(
                    "Failed to remove temp publish item \"{}\"".format(
                        item_id
                    ),
                    exc_info=True
                )

    def clear(self):
        self.cleanup(False)

    def get_items(self):
        output = []
        data = self._get_data()
        for item_id, item_data in data.items():
            item_path = os.path.join(self._root_dir, item_id)
            output.append(TempPublishFilesItem(item_id, item_data, item_path))
        return output

    def remove_id(self, item_id):
        filepath = os.path.join(self._root_dir, item_id)
        if os.path.exists(filepath):
            shutil.rmtree(filepath)

        with self._modify_data() as data:
            data.pop(item_id, None)


def file_size_to_string(file_size):
    size = 0
    size_ending_mapping = {
        "KB": 1024 ** 1,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3
    }
    ending = "B"
    for _ending, _size in size_ending_mapping.items():
        if file_size < _size:
            break
        size = file_size / _size
        ending = _ending
    return "{:.2f} {}".format(size, ending)
