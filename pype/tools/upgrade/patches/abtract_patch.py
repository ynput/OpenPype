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

    def get_report_record_base(self):
        """
            Skeleton for reporting to db.
        Returns:
            (dictionary): pre-filled from properties
        """
        rec = {}
        rec["version"] = self.version
        rec["affects"] = self.affects
        rec["description"] = self.description
        rec["implemented_by_PR"] = self.implemented_by_PR

        return rec

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

    # properties - set in implementing class as a class variables, not inside
    # of init (that would result in infinitive recursion error)
    @property
    def version(self):
        """ Version of Pype this patch brings to """
        return self.version

    @version.setter
    def version(self, val):
        self.version = val

    @property
    def affects(self):
        """ This patch changes 'avalon_db', 'pype_db'... """
        return self.affects

    @affects.setter
    def affects(self, val):
        self.affects = val

    @property
    def description(self):
        """ What kind of changes per 'affects' keys """
        return self.description

    @description.setter
    def description(self, val):
        self.description = val

    @property
    def applied_on(self):
        """ Applied 'global'(not project change)|'project_A'... """
        return self.applied_on

    @applied_on.setter
    def applied_on(self, val):
        self.applied_on = val

    @property
    def implemented_by_PR(self):
        """ Pull request id that implements this patch """
        return self.implemented_by_PR

    @implemented_by_PR.setter
    def implemented_by_PR(self, val):
        self.implemented_by_PR = val
