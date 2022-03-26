import os
import logging
import sys
import errno
import six

from openpype.lib import create_hard_link

# this is needed until speedcopy for linux is fixed
if sys.platform == "win32":
    from speedcopy import copyfile
else:
    from shutil import copyfile


class FileTransaction(object):
    """

    The file transaction is a three step process.

    1) Rename any existing files to a "temporary backup" during `process()`
    2) Copy the files to final destination during `process()`
    3) Remove any backed up files (*no rollback possible!) during `finalize()`

    Step 3 is done during `finalize()`. If not called the .bak files will
    remain on disk.

    These steps try to ensure that we don't overwrite half of any existing
    files e.g. if they are currently in use.

    Note:
        A regular filesystem is *not* a transactional file system and even
        though this implementation tries to produce a 'safe copy' with a
        potential rollback do keep in mind that it's inherently unsafe due
        to how filesystem works and a myriad of things could happen during
        the transaction that break the logic. A file storage could go down,
        permissions could be changed, other machines could be moving or writing
        files. A lot can happen.

    Warning:
        Any folders created during the transfer will not be removed.

    """

    MODE_COPY = 0
    MODE_HARDLINK = 1

    def __init__(self, log=None):

        if log is None:
            log = logging.getLogger("FileTransaction")

        self.log = log

        # The transfer queue
        # todo: make this an actual FIFO queue?
        self._transfers = {}

        # Destination file paths that a file was transferred to
        self._transferred = []

        # Backup file location mapping to original locations
        self._backup_to_original = {}

    def add(self, src, dst, mode=MODE_COPY):
        """Add a new file to transfer queue"""
        opts = {"mode": mode}

        src = os.path.normpath(src)
        dst = os.path.normpath(dst)

        if dst in self._transfers:
            queued_src = self._transfers[dst][0]
            if src == queued_src:
                self.log.debug("File transfer was already "
                               "in queue: {} -> {}".format(src, dst))
                return
            else:
                self.log.warning("File transfer in queue replaced..")
                self.log.debug("Removed from queue: "
                               "{} -> {}".format(queued_src, dst))
                self.log.debug("Added to queue: {} -> {}".format(src, dst))

        self._transfers[dst] = (src, opts)

    def process(self):

        # Backup any existing files
        for dst in self._transfers.keys():
            if os.path.exists(dst):
                # Backup original file
                # todo: add timestamp or uuid to ensure unique
                backup = dst + ".bak"
                self._backup_to_original[backup] = dst
                self.log.debug("Backup existing file: "
                               "{} -> {}".format(dst, backup))
                os.rename(dst, backup)

        # Copy the files to transfer
        for dst, (src, opts) in self._transfers.items():
            self._create_folder_for_file(dst)

            if opts["mode"] == self.MODE_COPY:
                self.log.debug("Copying file ... {} -> {}".format(src, dst))
                copyfile(src, dst)
            elif opts["mode"] == self.MODE_HARDLINK:
                self.log.debug("Hardlinking file ... {} -> {}".format(src,
                                                                      dst))
                create_hard_link(src, dst)

            self._transferred.append(dst)

    def finalize(self):
        # Delete any backed up files
        for backup in self._backup_to_original.keys():
            try:
                os.remove(backup)
            except OSError:
                self.log.error("Failed to remove backup file: "
                               "{}".format(backup),
                               exc_info=True)

    def rollback(self):

        errors = 0

        # Rollback any transferred files
        for path in self._transferred:
            try:
                os.remove(path)
            except OSError:
                errors += 1
                self.log.error("Failed to rollback created file: "
                               "{}".format(path),
                               exc_info=True)

        # Rollback the backups
        for backup, original in self._backup_to_original.items():
            try:
                os.rename(backup, original)
            except OSError:
                errors += 1
                self.log.error("Failed to restore original file: "
                               "{} -> {}".format(backup, original),
                               exc_info=True)

        if errors:
            self.log.error("{} errors occurred during "
                           "rollback.".format(errors), exc_info=True)
            six.reraise(*sys.exc_info())

    @property
    def transferred(self):
        """Return the processed transfers destination paths"""
        return list(self._transferred)

    @property
    def backups(self):
        """Return the backup file paths"""
        return list(self._backup_to_original.keys())

    def _create_folder_for_file(self, path):
        dirname = os.path.dirname(path)
        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                self.log.critical("An unexpected error occurred.")
                six.reraise(*sys.exc_info())
