from abc import ABCMeta, abstractmethod


class AbstractProvider(metaclass=ABCMeta):

    @abstractmethod
    def is_active(self):
        """
            Returns True if provider is activated, eg. has working credentials.
        Returns:
            (boolean)
        """

    @abstractmethod
    def upload_file(self, source_path, target_path, overwrite=True):
        """
            Copy file from 'source_path' to 'target_path' on provider.
            Use 'overwrite' boolean to rewrite existing file on provider

        Args:
            source_path (string): absolute path on local system
            target_path (string): absolute path on provider (GDrive etc.)
            overwrite (boolean): True if overwite existing
        Returns:
            (string) file_id of created file, raises exception
        """
        pass

    @abstractmethod
    def download_file(self, source_path, local_path):
        """
            Download file from provider into local system

        Args:
            source_path (string): absolute path on provider
            local_path (string): absolute path on local
        Returns:
            None
        """
        pass

    @abstractmethod
    def delete_file(self, path):
        """
            Deletes file from 'path'. Expects path to specific file.

        Args:
            path (string): absolute path to particular file

        Returns:
            None
        """
        pass

    @abstractmethod
    def list_folder(self, folder_path):
        """
            List all files and subfolders of particular path non-recursively.
        Args:
            folder_path (string): absolut path on provider

        Returns:
            (list)
        """
        pass
