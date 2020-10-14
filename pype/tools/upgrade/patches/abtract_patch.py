from abc import ABCMeta, abstractmethod
from pype.api import Logger
log = Logger().get_logger("UpgradeExecutor")


class AbstractPatch(metaclass=ABCMeta):
    """
        Abstract class which structure all patches should follow.
        Main two methods to use or re-implement:
            run_global - changes not affecting specific project
            run_on_project - changes that should be run on project, could be
                run repeatedly, once per project

        It provides couple of helpful methods that are applicable for any
        patch(get_report_record_base). These are not expected to be
        overriden (but could be).
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
    def run_global(self):
        """
            Basic implementation of updates that should be run globally, eg.
            they are not affecting projects.
            It is expected that concrete Patches could override this method
            for any different use case.

            None of the called methods should raise any exceptions, each
            implemented method is responsible to wrap code into try-except
            block.
            In case of any error (False, str(exception) should be returned.

        Returns:
            (bool, string) - success, error message
        """
        result, error = self.update_avalon_global()
        if not result:
            return result, error
        result, error = self.update_api()
        if not result:
            return result, error
        result, error = self.update_pype_db()
        return result, error

    @abstractmethod
    def run_on_project(self, project_name):
        """
            Basic implementation of patch that should be run on project(s).
            It is expected that these kind of updates can be run first on
            test project, only after successful run on production ones.
            It is expected that concrete Patches could override this method
            for any different use case.
        Args:
            project_name (string): project name (matches collection name)

        Returns:
            (bool, string) - success, error message
        """
        result, error = self.update_avalon_project(project_name)

        return result, error

    @abstractmethod
    def update_avalon_global(self):
        """
            Prepare and run queries that should be run on all projects.
            It is expected that concrete Patches will implement this method
            for patches that have project dependent changes.

        Returns:
            (boolean, string): (false, error message) if error - by default
                (True, '') is returned for basic implementation of
                'self.run_global' to work. Without re-implementation it is
                kind of like 'pass'
        """
        return True, ''

    @abstractmethod
    def update_avalon_project(self, project_name):
        """
            Prepare and run queries for specific 'project_name'.
            It is expected that concrete Patches will implement this method
            for patches that have project dependent changes.
        Args:
            project_name (string):

        Returns:
            (boolean, string): (false, error message) if error
        """
        return True, ''

    @abstractmethod
    def update_api(self, api=None):
        """
            Prepare and run updates on external API (ftrack for example)
        Args:
            api (string):TODO

        Returns:
            (boolean, string): (false, error message) if error
        """
        return True, ''

    @abstractmethod
    def update_pype_db(self):
        """
            Prepare and run updates on 'pype' database.
            For special cases.

        Returns:
            (boolean, string): (false, error message) if error
        """
        return True, ''

    @abstractmethod
    def update_settings_global(self):
        """
            Prepare and run updates of settings.

        Returns:
            (boolean, string): (false, error message) if error
        """
        return True, ''

    @abstractmethod
    def update_settings_project(self, project_name):
        """
            Prepare and run updates of settings.

        Args:
            project_name (string):

        Returns:
            (boolean, string): (false, error message) if error
        """
        return True, ''

    def is_affected(self, label):
        """
            Check if patch is affecting 'label' area
        Args:
            label (string): 'global'|'project'

        Returns:
            (string)
        """
        return label in self.affects

    def get_report_record_base(self):
        """
            Skeleton for reporting to db.
        Returns:
            (dictionary): pre-filled from properties
        """
        rec = {
            "name": self.name,
            "version": self.version,
            "affects": self.affects,
            "description": self.description,
            "implemented_by_PR": self.implemented_by_PR,
            "applied_on": {}
        }

        return rec

    def update_avalon_project_version(self, project_name, session=None):
        """
            Auxiliary function that logs to project document that this
            project was updated. For debugging purposes.
            It stores:
                ...
                "version": THIS_PATCH.version
                "patched_versions": [PREVIOUS_PATCH.version...]
        Args:
            project_name (string):
            session (MongoClient.session):

        """
        self.avalon_conn.Session["AVALON_PROJECT"] = project_name
        filter = {"type": "project"}
        project = self.avalon_conn.find_one(filter)
        previous_version = project.get("version", '1.0.0')
        patched_versions = project.get("patched_versions", [])
        patched_versions.append(previous_version)

        update_object = {"$set": {"version": self.version,
                                  "patched_versions": patched_versions}}

        self.avalon_conn.update_one(filter, update_object,
                                    session=session)


    # properties - set in implementing class as a class variables, not inside
    # of init (that would result in infinitive recursion error)
    @property
    def name(self):
        """ Version of Pype this patch brings to """
        return self.name

    @name.setter
    def name(self, val):
        self.name = val

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
        """ Applied 'global'(not project change)|'project_A'...

            In DB:
            ...
            applied_on: {
                            "global": 01.01.2020 00:00:00,
                            "project_A": 01.01.2020 00:00:00
                        }
        """
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
