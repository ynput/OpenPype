import sys
import six
import pyblish.api
from openpype.lib.file_transaction import (
    FileTransaction,
    DuplicateDestinationError
)
from openpype.pipeline.publish import (
    KnownPublishError
)


class ExtractStagingDirMigrate(pyblish.api.InstancePlugin):

    label = "Extract Staging Dir Migrate"
    order = pyblish.api.ExtractorOrder

    def process(self, instance):

        # get staging dir migrate key from instance data
        staging_dir_migrate = instance.data.get("stagingDirMigrateFiles")

        # if key does not exist then we do not need to do anything
        # and we can return
        if not staging_dir_migrate:
            return

        # use file transaction to copy files from source to destination
        # with ability to rollback in case something goes wrong
        file_transactions = FileTransaction(
            log=self.log,
            # Enforce unique transfers
            allow_queue_replacements=False
        )
        try:
            self.register_files(file_transactions, staging_dir_migrate)
        except DuplicateDestinationError as exc:
            # Raise DuplicateDestinationError as KnownPublishError
            # and rollback the transactions
            file_transactions.rollback()
            six.reraise(KnownPublishError,
                        KnownPublishError(exc),
                        sys.exc_info()[2])
        except Exception:
            # clean destination
            # todo: preferably we'd also rollback *any* changes to the database
            file_transactions.rollback()
            self.log.critical("Error when registering", exc_info=True)
            six.reraise(*sys.exc_info())

        # Finalizing can't rollback safely so no use for moving it to
        # the try, except.
        file_transactions.finalize()

    def register_files(self, file_transactions, transfer_files):
        """Register files for transfer.

        Args:
            file_transactions (FileTransaction): FileTransaction instance
            transfer_files (List[Dict]): List of dictionaries
                                         with src and dst keys
        """

        # iterate all dictionaries in list with src an dst keys and copy files
        # from src to dst
        for f_ in transfer_files:
            self.log.debug(
                "Copying file from: {} to: {}".format(f_["src"], f_["dst"])
            )
            file_transactions.add(f_["src"], f_["dst"])

        file_transactions.process()
