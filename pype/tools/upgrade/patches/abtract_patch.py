from abc import ABCMeta, abstractmethod
from pype.api import Logger
log = Logger().get_logger("UpgradeExecutor")

class AbstractPatch(metaclass=ABCMeta):
    """
        Abstract class which structure all patches should follow.
    """

    @abstractmethod
    def __init__(self, avalon_connection=None, pype_connection=None):
        """
            Inject connected collection object to run db operations on.
        Args:
            avalon_connection (AvalonMongoDB):
            pype_connection (PypeMongoDB):
        """

    @abstractmethod
    def update_avalon_global(self):
        """
            Prepare and run queries that should be run on all projects.

        Returns:
            (boolean, string): (false, error message) if error
        """
        pass

    @abstractmethod
    def update_avalon_project(self, project_name):
        """
            Prepare and run queries for specific 'project_name'
        Args:
            project_name (string):

        Returns:
            (boolean, string): (false, error message) if error
        """
        pass

    @abstractmethod
    def update_api(self, api):
        """
            Prepare and run updates on external API (ftrack for example)
        Args:
            api (string):TODO

        Returns:
            (boolean, string): (false, error message) if error
        """

    @abstractmethod
    def update_pype_db(self):
        """
            Prepare and run updates on 'pype' database.
            For special cases.

        Returns:
            (boolean, string): (false, error message) if error
        """

    @abstractmethod
    def run(self, projects=[]):
        """
            Runs all implemented method in sequence. Next step is triggered
            only if previous finished successfully.
            Logs errors into DB.
        Args:
            projects (list): projects names for 'update_avalon_project'
        Returns:
            (boolean, string): true if all OK, (false, error_message) otherwise
        """
        # if self.update_avalon_global():
        #     if self.update_avalon_project():
        #         if self.update_api():
        #             if self.update_pype_db():
        #                 pass
