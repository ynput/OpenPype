from abc import ABCMeta, abstractmethod


class AbstractProvider(metaclass=ABCMeta):

    @abstractmethod
    def upload_file(self, source_path, target_path, overwrite=True):
        """
            Copy file from 'source_path' to 'target_path' on provider.
            Use 'overwrite' boolean to rewrite existing file on provider
        :param source_path: absolute path on local system
        :param target_path: absolute path on provider (GDrive etc.)
        :param overwrite: <boolean> True if overwite existing
        :return: <string> file_id of created file, raises exception
        """
        pass

    @abstractmethod
    def download_file(self, source_path, local_path):
        """
            Download file from provider into local system
        :param source_path: absolute path on provider
        :param local_path: absolute path on local
        :return:
        """
        pass

    @abstractmethod
    def delete_file(self, path):
        """
            Deletes file from 'path'. Expects path to specific file.
        :param path: absolute path to particular file
        :return: None
        """
        pass

    @abstractmethod
    def list_folder(self, folder_path):
        """
            List all files and subfolders of particular path non-recursively.
        :param folder_path: absolut path on provider
        :return: <list>
        """
        pass