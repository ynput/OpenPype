from abc import ABCMeta, abstractmethod


class AbstractProvider(metaclass=ABCMeta):

    def __init__(self, site_name, tree=None, presets=None):
        self.presets = None
        self.active = False
        self.site_name = site_name

        self.presets = presets

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
    def download_file(self, source_path, local_path, overwrite=True):
        """
            Download file from provider into local system

        Args:
            source_path (string): absolute path on provider
            local_path (string): absolute path on local
            overwrite (bool): default set to True
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

    @abstractmethod
    def create_folder(self, folder_path):
        """
            Create all nonexistent folders and subfolders in 'path'.

        Args:
            path (string): absolute path

        Returns:
            (string) folder id of lowest subfolder from 'path'
        """
        pass

    @abstractmethod
    def get_tree(self):
        """
            Creates folder structure for providers which do not provide
            tree folder structure (GDrive has no accessible tree structure,
            only parents and their parents)
        """
        pass

    @abstractmethod
    def resolve_path(self, path, root_config, anatomy=None):
        """
            Replaces root placeholders with appropriate real value from
            'root_configs' (from Settings or Local Settings) or Anatomy
            (mainly for 'studio' site)

            Args:
                path(string): path with '{root[work]}/...'
                root_config(dict): from Settings or Local Settings
                anatomy (Anatomy): prepared anatomy object for project
        """
        pass
