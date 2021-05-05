import os
from bson.objectid import ObjectId
from datetime import datetime
import threading

from avalon.api import AvalonMongoDB

from .. import PypeModule, ITrayModule
from openpype.api import (
    Anatomy,
    get_project_settings,
    get_local_site_id)
from openpype.lib import PypeLogger

from .providers.local_drive import LocalDriveHandler

from .utils import time_function, SyncStatus


log = PypeLogger().get_logger("SyncServer")


class SyncServerModule(PypeModule, ITrayModule):
    """
       Synchronization server that is syncing published files from local to
       any of implemented providers (like GDrive, S3 etc.)
       Runs in the background and checks all representations, looks for files
       that are marked to be in different location than 'studio' (temporary),
       checks if 'created_dt' field is present denoting successful sync
       with provider destination.
       Sites structure is created during publish OR by calling 'add_site'
       method.

       By default it will always contain 1 record with
       "name" ==  self.presets["active_site"] and
       filled "created_dt" AND 1 or multiple records for all defined
       remote sites, where "created_dt" is not present.
       This highlights that file should be uploaded to
       remote destination

       ''' - example of synced file test_Cylinder_lookMain_v010.ma to GDrive
        "files" : [
        {
            "path" : "{root}/Test/Assets/Cylinder/publish/look/lookMain/v010/
                     test_Cylinder_lookMain_v010.ma",
            "_id" : ObjectId("5eeb25e411e06a16209ab78f"),
            "hash" : "test_Cylinder_lookMain_v010,ma|1592468963,24|4822",
            "size" : NumberLong(4822),
            "sites" : [
                {
                    "name": "john_local_XD4345",
                    "created_dt" : ISODate("2020-05-22T08:05:44.000Z")
                },
                {
                    "id" : ObjectId("5eeb25e411e06a16209ab78f"),
                    "name": "gdrive",
                    "created_dt" : ISODate("2020-05-55T08:54:35.833Z")
                ]
            }
        },
        '''
        Each Tray app has assigned its own  self.presets["local_id"]
        used in sites as a name.
        Tray is searching only for records where name matches its
        self.presets["active_site"] + self.presets["remote_site"].
        "active_site" could be storage in studio ('studio'), or specific
        "local_id" when user is working disconnected from home.
        If the local record has its "created_dt" filled, it is a source and
        process will try to upload the file to all defined remote sites.

        Remote files "id" is real id that could be used in appropriate API.
        Local files have "id" too, for conformity, contains just file name.
        It is expected that multiple providers will be implemented in separate
        classes and registered in 'providers.py'.

    """
    # limit querying DB to look for X number of representations that should
    # be sync, we try to run more loops with less records
    # actual number of files synced could be lower as providers can have
    # different limits imposed by its API
    # set 0 to no limit
    REPRESENTATION_LIMIT = 100
    DEFAULT_SITE = 'studio'
    LOCAL_SITE = 'local'
    LOG_PROGRESS_SEC = 5  # how often log progress to DB
    DEFAULT_PRIORITY = 50  # higher is better, allowed range 1 - 1000

    name = "sync_server"
    label = "Sync Queue"

    def initialize(self, module_settings):
        """
            Called during Module Manager creation.

            Collects needed data, checks asyncio presence.
            Sets 'enabled' according to global settings for the module.
            Shouldnt be doing any initialization, thats a job for 'tray_init'
        """
        self.enabled = module_settings[self.name]["enabled"]

        # some parts of code need to run sequentially, not in async
        self.lock = None
        # settings for all enabled projects for sync
        self._sync_project_settings = None
        self.sync_server_thread = None  # asyncio requires new thread

        self.action_show_widget = None
        self._paused = False
        self._paused_projects = set()
        self._paused_representations = set()
        self._anatomies = {}

        self._connection = None

    """ Start of Public API """
    def add_site(self, collection, representation_id, site_name=None,
                 force=False):
        """
            Adds new site to representation to be synced.

            'collection' must have synchronization enabled (globally or
            project only)

            Used as a API endpoint from outside applications (Loader etc)

            Args:
                collection (string): project name (must match DB)
                representation_id (string): MongoDB _id value
                site_name (string): name of configured and active site
                force (bool): reset site if exists

            Returns:
                throws ValueError if any issue
        """
        if not self.get_sync_project_setting(collection):
            raise ValueError("Project not configured")

        if not site_name:
            site_name = self.DEFAULT_SITE

        self.reset_provider_for_file(collection,
                                     representation_id,
                                     site_name=site_name, force=force)

    # public facing API
    def remove_site(self, collection, representation_id, site_name,
                    remove_local_files=False):
        """
            Removes 'site_name' for particular 'representation_id' on
            'collection'

            Args:
                collection (string): project name (must match DB)
                representation_id (string): MongoDB _id value
                site_name (string): name of configured and active site
                remove_local_files (bool): remove only files for 'local_id'
                    site

            Returns:
                throws ValueError if any issue
        """
        if not self.get_sync_project_setting(collection):
            raise ValueError("Project not configured")

        self.reset_provider_for_file(collection,
                                     representation_id,
                                     site_name=site_name,
                                     remove=True)
        if remove_local_files:
            self._remove_local_file(collection, representation_id, site_name)

    def clear_project(self, collection, site_name):
        """
            Clear 'collection' of 'site_name' and its local files

            Works only on real local sites, not on 'studio'
        """
        query = {
            "type": "representation",
            "files.sites.name": site_name
        }

        representations = list(
            self.connection.database[collection].find(query))
        if not representations:
            self.log.debug("No repre found")
            return

        for repre in representations:
            self.remove_site(collection, repre.get("_id"), site_name, True)

    def pause_representation(self, collection, representation_id, site_name):
        """
            Sets 'representation_id' as paused, eg. no syncing should be
            happening on it.

            Args:
                collection (string): project name
                representation_id (string): MongoDB objectId value
                site_name (string): 'gdrive', 'studio' etc.
        """
        log.info("Pausing SyncServer for {}".format(representation_id))
        self._paused_representations.add(representation_id)
        self.reset_provider_for_file(collection, representation_id,
                                     site_name=site_name, pause=True)

    def unpause_representation(self, collection, representation_id, site_name):
        """
            Sets 'representation_id' as unpaused.

            Does not fail or warn if repre wasn't paused.

            Args:
                collection (string): project name
                representation_id (string): MongoDB objectId value
                site_name (string): 'gdrive', 'studio' etc.
        """
        log.info("Unpausing SyncServer for {}".format(representation_id))
        try:
            self._paused_representations.remove(representation_id)
        except KeyError:
            pass
        # self.paused_representations is not persistent
        self.reset_provider_for_file(collection, representation_id,
                                     site_name=site_name, pause=False)

    def is_representation_paused(self, representation_id,
                                 check_parents=False, project_name=None):
        """
            Returns if 'representation_id' is paused or not.

            Args:
                representation_id (string): MongoDB objectId value
                check_parents (bool): check if parent project or server itself
                    are not paused
                project_name (string): project to check if paused

                if 'check_parents', 'project_name' should be set too
            Returns:
                (bool)
        """
        condition = representation_id in self._paused_representations
        if check_parents and project_name:
            condition = condition or \
                self.is_project_paused(project_name) or \
                self.is_paused()
        return condition

    def pause_project(self, project_name):
        """
            Sets 'project_name' as paused, eg. no syncing should be
            happening on all representation inside.

            Args:
                project_name (string): collection name
        """
        log.info("Pausing SyncServer for {}".format(project_name))
        self._paused_projects.add(project_name)

    def unpause_project(self, project_name):
        """
            Sets 'project_name' as unpaused

            Does not fail or warn if project wasn't paused.

            Args:
                project_name (string): collection name
        """
        log.info("Unpausing SyncServer for {}".format(project_name))
        try:
            self._paused_projects.remove(project_name)
        except KeyError:
            pass

    def is_project_paused(self, project_name, check_parents=False):
        """
            Returns if 'project_name' is paused or not.

            Args:
                project_name (string): collection name
                check_parents (bool): check if server itself
                    is not paused
            Returns:
                (bool)
        """
        condition = project_name in self._paused_projects
        if check_parents:
            condition = condition or self.is_paused()
        return condition

    def pause_server(self):
        """
            Pause sync server

            It won't check anything, not uploading/downloading...
        """
        log.info("Pausing SyncServer")
        self._paused = True

    def unpause_server(self):
        """
            Unpause server
        """
        log.info("Unpausing SyncServer")
        self._paused = False

    def is_paused(self):
        """ Is server paused """
        return self._paused

    def get_active_sites(self, project_name):
        """
            Returns list of active sites for 'project_name'.

            By default it returns ['studio'], this site is default
            and always present even if SyncServer is not enabled. (for publish)

            Used mainly for Local settings for user override.

            Args:
                project_name (string):

            Returns:
                (list) of strings
        """
        return self.get_active_sites_from_settings(
            get_project_settings(project_name))

    def get_active_sites_from_settings(self, settings):
        """
            List available active sites from incoming 'settings'. Used for
            returning 'default' values for Local Settings

            Args:
                settings (dict): full settings (global + project)
            Returns:
                (list) of strings
        """
        sync_settings = self._parse_sync_settings_from_settings(settings)

        return self._get_enabled_sites_from_settings(sync_settings)

    def get_configurable_items_for_site(self, project_name, site_name):
        """
            Returns list of items that should be configurable by User

            Returns:
                (list of dict)
                [{key:"root", label:"root", value:"valueFromSettings"}]
        """
        # if project_name is None: ..for get_default_project_settings
        # return handler.get_configurable_items()
        pass

    def get_active_site(self, project_name):
        """
            Returns active (mine) site for 'project_name' from settings

            Returns:
                (string)
        """
        active_site = self.get_sync_project_setting(
            project_name)['config']['active_site']
        if active_site == self.LOCAL_SITE:
            return get_local_site_id()
        return active_site

    # remote sites
    def get_remote_sites(self, project_name):
        """
            Returns all remote sites configured on 'project_name'.

            If 'project_name' is not enabled for syncing returns [].

            Used by Local setting to allow user choose remote site.

            Args:
                project_name (string):

            Returns:
                (list) of strings
        """
        return self.get_remote_sites_from_settings(
            get_project_settings(project_name))

    def get_remote_sites_from_settings(self, settings):
        """
            Get remote sites for returning 'default' values for Local Settings
        """
        sync_settings = self._parse_sync_settings_from_settings(settings)

        return self._get_remote_sites_from_settings(sync_settings)

    def get_remote_site(self, project_name):
        """
            Returns remote (theirs) site for 'project_name' from settings
        """
        remote_site = self.get_sync_project_setting(
            project_name)['config']['remote_site']
        if remote_site == self.LOCAL_SITE:
            return get_local_site_id()

        return remote_site

    def reset_timer(self):
        """
            Called when waiting for next loop should be skipped.

            In case of user's involvement (reset site), start that right away.
        """
        self.sync_server_thread.reset_timer()

    def get_enabled_projects(self):
        """Returns list of projects which have SyncServer enabled."""
        enabled_projects = []
        for project in self.connection.projects():
            project_name = project["name"]
            project_settings = self.get_sync_project_setting(project_name)
            if project_settings:
                enabled_projects.append(project_name)

        return enabled_projects
    """ End of Public API """

    def get_local_file_path(self, collection, site_name, file_path):
        """
            Externalized for app
        """
        handler = LocalDriveHandler(collection, site_name)
        local_file_path = handler.resolve_path(file_path)

        return local_file_path

    def _get_remote_sites_from_settings(self, sync_settings):
        if not self.enabled or not sync_settings.get('enabled'):
            return []

        remote_sites = [self.DEFAULT_SITE, self.LOCAL_SITE]
        if sync_settings:
            remote_sites.extend(sync_settings.get("sites").keys())

        return list(set(remote_sites))

    def _get_enabled_sites_from_settings(self, sync_settings):
        sites = [self.DEFAULT_SITE]
        if self.enabled and sync_settings.get('enabled'):
            sites.append(self.LOCAL_SITE)

        return sites

    def connect_with_modules(self, *_a, **kw):
        return

    def tray_init(self):
        """
            Actual initialization of Sync Server.

            Called when tray is initialized, it checks if module should be
            enabled. If not, no initialization necessary.
        """
        # import only in tray, because of Python2 hosts
        from .sync_server import SyncServerThread

        if not self.enabled:
            return

        enabled_projects = self.get_enabled_projects()
        if not enabled_projects:
            self.enabled = False
            return

        self.lock = threading.Lock()

        try:
            self.sync_server_thread = SyncServerThread(self)

            from .tray.app import SyncServerWindow
            self.widget = SyncServerWindow(self)
        except ValueError:
            log.info("No system setting for sync. Not syncing.", exc_info=True)
            self.enabled = False
        except KeyError:
            log.info((
                "There are not set presets for SyncServer OR "
                "Credentials provided are invalid, "
                "no syncing possible").
                format(str(self.sync_project_settings)), exc_info=True)
            self.enabled = False

    def tray_start(self):
        """
            Triggered when Tray is started.

            Checks if configuration presets are available and if there is
            any provider ('gdrive', 'S3') that is activated
            (eg. has valid credentials).

        Returns:
            None
        """
        if self.sync_project_settings and self.enabled:
            self.sync_server_thread.start()
        else:
            log.info("No presets or active providers. " +
                     "Synchronization not possible.")

    def tray_exit(self):
        """
            Stops sync thread if running.

            Called from Module Manager
        """
        if not self.sync_server_thread:
            return

        if not self.is_running:
            return
        try:
            log.info("Stopping sync server server")
            self.sync_server_thread.is_running = False
            self.sync_server_thread.stop()
        except Exception:
            log.warning(
                "Error has happened during Killing sync server",
                exc_info=True
            )

    def tray_menu(self, parent_menu):
        if not self.enabled:
            return

        from Qt import QtWidgets
        """Add menu or action to Tray(or parent)'s menu"""
        action = QtWidgets.QAction(self.label, parent_menu)
        action.triggered.connect(self.show_widget)
        parent_menu.addAction(action)
        parent_menu.addSeparator()

        self.action_show_widget = action

    @property
    def is_running(self):
        return self.sync_server_thread.is_running

    def get_anatomy(self, project_name):
        """
            Get already created or newly created anatomy for project

            Args:
                project_name (string):

            Return:
                (Anatomy)
        """
        return self._anatomies.get('project_name') or Anatomy(project_name)

    @property
    def connection(self):
        if self._connection is None:
            self._connection = AvalonMongoDB()

        return self._connection

    @property
    def sync_project_settings(self):
        if self._sync_project_settings is None:
            self.set_sync_project_settings()

        return self._sync_project_settings

    def set_sync_project_settings(self):
        """
            Set sync_project_settings for all projects (caching)

            For performance
        """
        sync_project_settings = {}

        for collection in self.connection.database.collection_names(False):
            sync_settings = self._parse_sync_settings_from_settings(
                get_project_settings(collection))
            if sync_settings:
                default_sites = self._get_default_site_configs()
                sync_settings['sites'].update(default_sites)
                sync_project_settings[collection] = sync_settings

        if not sync_project_settings:
            log.info("No enabled and configured projects for sync.")

        self._sync_project_settings = sync_project_settings

    def get_sync_project_setting(self, project_name):
        """ Handles pulling sync_server's settings for enabled 'project_name'

            Args:
                project_name (str): used in project settings
            Returns:
                (dict): settings dictionary for the enabled project,
                    empty if no settings or sync is disabled
        """
        # presets set already, do not call again and again
        # self.log.debug("project preset {}".format(self.presets))
        if self.sync_project_settings and \
                self.sync_project_settings.get(project_name):
            return self.sync_project_settings.get(project_name)

        settings = get_project_settings(project_name)
        return self._parse_sync_settings_from_settings(settings)

    def _parse_sync_settings_from_settings(self, settings):
        """ settings from api.get_project_settings, TOOD rename """
        sync_settings = settings.get("global").get("sync_server")
        if not sync_settings:
            log.info("No project setting not syncing.")
            return {}
        if sync_settings.get("enabled"):
            return sync_settings

        return {}

    def _get_default_site_configs(self):
        """
            Returns skeleton settings for 'studio' and user's local site
        """
        default_config = {'provider': 'local_drive'}
        all_sites = {self.DEFAULT_SITE: default_config,
                     get_local_site_id(): default_config}
        return all_sites

    def get_provider_for_site(self, project_name, site):
        """
            Return provider name for site.
        """
        site_preset = self.get_sync_project_setting(project_name)["sites"].\
            get(site)
        if site_preset:
            return site_preset["provider"]

        return "NA"

    @time_function
    def get_sync_representations(self, collection, active_site, remote_site):
        """
            Get representations that should be synced, these could be
            recognised by presence of document in 'files.sites', where key is
            a provider (GDrive, S3) and value is empty document or document
            without 'created_dt' field. (Don't put null to 'created_dt'!).

            Querying of 'to-be-synched' files is offloaded to Mongod for
            better performance. Goal is to get as few representations as
            possible.
        Args:
            collection (string): name of collection (in most cases matches
                project name
            active_site (string): identifier of current active site (could be
                'local_0' when working from home, 'studio' when working in the
                studio (default)
            remote_site (string): identifier of remote site I want to sync to

        Returns:
            (list) of dictionaries
        """
        log.debug("Check representations for : {}".format(collection))
        self.connection.Session["AVALON_PROJECT"] = collection
        # retry_cnt - number of attempts to sync specific file before giving up
        retries_arr = self._get_retries_arr(collection)
        match = {
            "type": "representation",
            "$or": [
                {"$and": [
                    {
                        "files.sites": {
                            "$elemMatch": {
                                "name": active_site,
                                "created_dt": {"$exists": True}
                            }
                        }}, {
                        "files.sites": {
                            "$elemMatch": {
                                "name": {"$in": [remote_site]},
                                "created_dt": {"$exists": False},
                                "tries": {"$in": retries_arr}
                            }
                        }
                    }]},
                {"$and": [
                    {
                        "files.sites": {
                            "$elemMatch": {
                                "name": active_site,
                                "created_dt": {"$exists": False},
                                "tries": {"$in": retries_arr}
                            }
                        }}, {
                        "files.sites": {
                            "$elemMatch": {
                                "name": {"$in": [remote_site]},
                                "created_dt": {"$exists": True}
                            }
                        }
                    }
                ]}
            ]
        }

        aggr = [
            {"$match": match},
            {'$unwind': '$files'},
            {'$addFields': {
                'order_remote': {
                    '$filter': {'input': '$files.sites', 'as': 'p',
                                'cond': {'$eq': ['$$p.name', remote_site]}
                                }},
                'order_local': {
                    '$filter': {'input': '$files.sites', 'as': 'p',
                                'cond': {'$eq': ['$$p.name', active_site]}
                                }},
            }},
            {'$addFields': {
                'priority': {
                    '$cond': [
                        {'$size': '$order_local.priority'},
                        {'$first': '$order_local.priority'},
                        {'$cond': [
                            {'$size': '$order_remote.priority'},
                            {'$first': '$order_remote.priority'},
                            self.DEFAULT_PRIORITY]}
                    ]
                },
            }},
            {'$group': {
                '_id': '$_id',
                # pass through context - same for representation
                'context': {'$addToSet': '$context'},
                'data': {'$addToSet': '$data'},
                # pass through files as a list
                'files': {'$addToSet': '$files'},
                'priority': {'$max': "$priority"},
            }},
            {"$sort": {'priority': -1, '_id': 1}},
        ]
        log.debug("active_site:{} - remote_site:{}".format(active_site,
                                                           remote_site))
        log.debug("query: {}".format(aggr))
        representations = self.connection.aggregate(aggr)

        return representations

    def check_status(self, file, local_site, remote_site, config_preset):
        """
            Check synchronization status for single 'file' of single
            'representation' by single 'provider'.
            (Eg. check if 'scene.ma' of lookdev.v10 should be synced to GDrive

            Always is comparing local record, eg. site with
            'name' == self.presets[PROJECT_NAME]['config']["active_site"]

        Args:
            file (dictionary):  of file from representation in Mongo
            local_site (string):  - local side of compare (usually 'studio')
            remote_site (string):  - gdrive etc.
            config_preset (dict): config about active site, retries
        Returns:
            (string) - one of SyncStatus
        """
        sites = file.get("sites") or []
        # if isinstance(sites, list):  # temporary, old format of 'sites'
        #     return SyncStatus.DO_NOTHING
        _, remote_rec = self._get_site_rec(sites, remote_site) or {}
        if remote_rec:  # sync remote target
            created_dt = remote_rec.get("created_dt")
            if not created_dt:
                tries = self._get_tries_count_from_rec(remote_rec)
                # file will be skipped if unsuccessfully tried over threshold
                # error metadata needs to be purged manually in DB to reset
                if tries < int(config_preset["retry_cnt"]):
                    return SyncStatus.DO_UPLOAD
            else:
                _, local_rec = self._get_site_rec(sites, local_site) or {}
                if not local_rec or not local_rec.get("created_dt"):
                    tries = self._get_tries_count_from_rec(local_rec)
                    # file will be skipped if unsuccessfully tried over
                    # threshold times, error metadata needs to be purged
                    # manually in DB to reset
                    if tries < int(config_preset["retry_cnt"]):
                        return SyncStatus.DO_DOWNLOAD

        return SyncStatus.DO_NOTHING

    def update_db(self, collection, new_file_id, file, representation,
                  site, error=None, progress=None, priority=None):
        """
            Update 'provider' portion of records in DB with success (file_id)
            or error (exception)

        Args:
            collection (string): name of project - force to db connection as
              each file might come from different collection
            new_file_id (string):
            file (dictionary): info about processed file (pulled from DB)
            representation (dictionary): parent repr of file (from DB)
            site (string): label ('gdrive', 'S3')
            error (string): exception message
            progress (float): 0-1 of progress of upload/download
            priority (int): 0-100 set priority

        Returns:
            None
        """
        representation_id = representation.get("_id")
        file_id = None
        if file:
            file_id = file.get("_id")

        query = {
            "_id": representation_id
        }

        update = {}
        if new_file_id:
            update["$set"] = self._get_success_dict(new_file_id)
            # reset previous errors if any
            update["$unset"] = self._get_error_dict("", "", "")
        elif progress is not None:
            update["$set"] = self._get_progress_dict(progress)
        elif priority is not None:
            update["$set"] = self._get_priority_dict(priority, file_id)
        else:
            tries = self._get_tries_count(file, site)
            tries += 1

            update["$set"] = self._get_error_dict(error, tries)

        arr_filter = [
            {'s.name': site}
        ]
        if file_id:
            arr_filter.append({'f._id': ObjectId(file_id)})

        self.connection.database[collection].update_one(
            query,
            update,
            upsert=True,
            array_filters=arr_filter
        )

        if progress is not None or priority is not None:
            return

        status = 'failed'
        error_str = 'with error {}'.format(error)
        if new_file_id:
            status = 'succeeded with id {}'.format(new_file_id)
            error_str = ''

        source_file = file.get("path", "")
        log.debug("File for {} - {source_file} process {status} {error_str}".
                  format(representation_id,
                         status=status,
                         source_file=source_file,
                         error_str=error_str))

    def _get_file_info(self, files, _id):
        """
            Return record from list of records which name matches to 'provider'
            Could be possibly refactored with '_get_provider_rec' together.

        Args:
            files (list): of dictionaries with info about published files
            _id (string): _id of specific file

        Returns:
            (int, dictionary): index from list and record with metadata
                               about site (if/when created, errors..)
            OR (-1, None) if not present
        """
        for index, rec in enumerate(files):
            if rec.get("_id") == _id:
                return index, rec

        return -1, None

    def _get_site_rec(self, sites, site_name):
        """
            Return record from list of records which name matches to
            'remote_site_name'

        Args:
            sites (list): of dictionaries
            site_name (string): 'local_XXX', 'gdrive'

        Returns:
            (int, dictionary): index from list and record with metadata
                               about site (if/when created, errors..)
            OR (-1, None) if not present
        """
        for index, rec in enumerate(sites):
            if rec.get("name") == site_name:
                return index, rec

        return -1, None

    def reset_provider_for_file(self, collection, representation_id,
                                side=None, file_id=None, site_name=None,
                                remove=False, pause=None, force=False):
        """
            Reset information about synchronization for particular 'file_id'
            and provider.
            Useful for testing or forcing file to be reuploaded.

            'side' and 'site_name' are disjunctive.

            'side' is used for resetting local or remote side for
            current user for repre.

            'site_name' is used to set synchronization for particular site.
            Should be used when repre should be synced to new site.

        Args:
            collection (string): name of project (eg. collection) in DB
            representation_id(string): _id of representation
            file_id (string):  file _id in representation
            side (string): local or remote side
            site_name (string): for adding new site
            remove (bool): if True remove site altogether
            pause (bool or None): if True - pause, False - unpause
            force (bool): hard reset - currently only for add_site

        Returns:
            throws ValueError
        """
        query = {
            "_id": ObjectId(representation_id)
        }

        representation = list(self.connection.database[collection].find(query))
        if not representation:
            raise ValueError("Representation {} not found in {}".
                             format(representation_id, collection))
        if side and site_name:
            raise ValueError("Misconfiguration, only one of side and " +
                             "site_name arguments should be passed.")

        local_site = self.get_active_site(collection)
        remote_site = self.get_remote_site(collection)

        if side:
            if side == 'local':
                site_name = local_site
            else:
                site_name = remote_site

        elem = {"name": site_name}

        if file_id:  # reset site for particular file
            self._reset_site_for_file(collection, query,
                                      elem, file_id, site_name)
        elif side:  # reset site for whole representation
            self._reset_site(collection, query, elem, site_name)
        elif remove:  # remove site for whole representation
            self._remove_site(collection, query, representation, site_name)
        elif pause is not None:
            self._pause_unpause_site(collection, query,
                                     representation, site_name, pause)
        else:  # add new site to all files for representation
            self._add_site(collection, query, representation, elem, site_name,
                           force)

    def _update_site(self, collection, query, update, arr_filter):
        """
            Auxiliary method to call update_one function on DB

            Used for refactoring ugly reset_provider_for_file
        """
        self.connection.database[collection].update_one(
            query,
            update,
            upsert=True,
            array_filters=arr_filter
        )

    def _reset_site_for_file(self, collection, query,
                             elem, file_id, site_name):
        """
            Resets 'site_name' for 'file_id' on representation in 'query' on
            'collection'
        """
        update = {
            "$set": {"files.$[f].sites.$[s]": elem}
        }
        arr_filter = [
            {'s.name': site_name},
            {'f._id': ObjectId(file_id)}
        ]

        self._update_site(collection, query, update, arr_filter)

    def _reset_site(self, collection, query, elem, site_name):
        """
            Resets 'site_name' for all files of representation in 'query'
        """
        update = {
            "$set": {"files.$[].sites.$[s]": elem}
        }

        arr_filter = [
            {'s.name': site_name}
        ]

        self._update_site(collection, query, update, arr_filter)

    def _remove_site(self, collection, query, representation, site_name):
        """
            Removes 'site_name' for 'representation' in 'query'

            Throws ValueError if 'site_name' not found on 'representation'
        """
        found = False
        for repre_file in representation.pop().get("files"):
            for site in repre_file.get("sites"):
                if site["name"] == site_name:
                    found = True
                    break
        if not found:
            msg = "Site {} not found".format(site_name)
            log.info(msg)
            raise ValueError(msg)

        update = {
            "$pull": {"files.$[].sites": {"name": site_name}}
        }
        arr_filter = []

        self._update_site(collection, query, update, arr_filter)

    def _pause_unpause_site(self, collection, query,
                            representation, site_name, pause):
        """
            Pauses/unpauses all files for 'representation' based on 'pause'

            Throws ValueError if 'site_name' not found on 'representation'
        """
        found = False
        site = None
        for repre_file in representation.pop().get("files"):
            for site in repre_file.get("sites"):
                if site["name"] == site_name:
                    found = True
                    break
        if not found:
            msg = "Site {} not found".format(site_name)
            log.info(msg)
            raise ValueError(msg)

        if pause:
            site['paused'] = pause
        else:
            if site.get('paused'):
                site.pop('paused')

        update = {
            "$set": {"files.$[].sites.$[s]": site}
        }

        arr_filter = [
            {'s.name': site_name}
        ]

        self._update_site(collection, query, update, arr_filter)

    def _add_site(self, collection, query, representation, elem, site_name,
                  force=False):
        """
            Adds 'site_name' to 'representation' on 'collection'

            Use 'force' to remove existing or raises ValueError
        """
        for repre_file in representation.pop().get("files"):
            for site in repre_file.get("sites"):
                if site["name"] == site_name:
                    if force:
                        self._reset_site_for_file(collection, query,
                                                  elem, repre_file["_id"],
                                                  site_name)
                        return
                    else:
                        msg = "Site {} already present".format(site_name)
                        log.info(msg)
                        raise ValueError(msg)

        update = {
            "$push": {"files.$[].sites": elem}
        }

        arr_filter = []

        self._update_site(collection, query, update, arr_filter)

    def _remove_local_file(self, collection, representation_id, site_name):
        """
            Removes all local files for 'site_name' of 'representation_id'

            Args:
                collection (string): project name (must match DB)
                representation_id (string): MongoDB _id value
                site_name (string): name of configured and active site

            Returns:
                only logs, catches IndexError and OSError
        """
        my_local_site = get_local_site_id()
        if my_local_site != site_name:
            self.log.warning("Cannot remove non local file for {}".
                             format(site_name))
            return

        provider_name = self.get_provider_for_site(collection, site_name)

        if provider_name == 'local_drive':
            query = {
                "_id": ObjectId(representation_id)
            }

            representation = list(
                self.connection.database[collection].find(query))
            if not representation:
                self.log.debug("No repre {} found".format(
                    representation_id))
                return

            representation = representation.pop()
            local_file_path = ''
            for file in representation.get("files"):
                local_file_path = self.get_local_file_path(collection,
                                                           site_name,
                                                           file.get("path", "")
                                                           )
                try:
                    self.log.debug("Removing {}".format(local_file_path))
                    os.remove(local_file_path)
                except IndexError:
                    msg = "No file set for {}".format(representation_id)
                    self.log.debug(msg)
                    raise ValueError(msg)
                except OSError:
                    msg = "File {} cannot be removed".format(file["path"])
                    self.log.warning(msg)
                    raise ValueError(msg)

            folder = None
            try:
                folder = os.path.dirname(local_file_path)
                os.rmdir(folder)
            except OSError:
                msg = "folder {} cannot be removed".format(folder)
                self.log.warning(msg)
                raise ValueError(msg)

    def get_loop_delay(self, project_name):
        """
            Return count of seconds before next synchronization loop starts
            after finish of previous loop.
        Returns:
            (int): in seconds
        """
        ld = self.sync_project_settings[project_name]["config"]["loop_delay"]
        return int(ld)

    def show_widget(self):
        """Show dialog to enter credentials"""
        self.widget.show()

    def _get_success_dict(self, new_file_id):
        """
            Provide success metadata ("id", "created_dt") to be stored in Db.
            Used in $set: "DICT" part of query.
            Sites are array inside of array(file), so real indexes for both
            file and site are needed for upgrade in DB.
        Args:
            new_file_id: id of created file
        Returns:
            (dictionary)
        """
        val = {"files.$[f].sites.$[s].id": new_file_id,
               "files.$[f].sites.$[s].created_dt": datetime.now()}
        return val

    def _get_error_dict(self, error="", tries="", progress=""):
        """
            Provide error metadata to be stored in Db.
            Used for set (error and tries provided) or unset mode.
        Args:
            error: (string) - message
            tries: how many times failed
        Returns:
            (dictionary)
        """
        val = {"files.$[f].sites.$[s].last_failed_dt": datetime.now(),
               "files.$[f].sites.$[s].error": error,
               "files.$[f].sites.$[s].tries": tries,
               "files.$[f].sites.$[s].progress": progress
               }
        return val

    def _get_tries_count_from_rec(self, rec):
        """
            Get number of failed attempts to sync from site record
        Args:
            rec (dictionary): info about specific site record
        Returns:
            (int) - number of failed attempts
        """
        if not rec:
            return 0
        return rec.get("tries", 0)

    def _get_tries_count(self, file, provider):
        """
            Get number of failed attempts to sync
        Args:
            file (dictionary): info about specific file
            provider (string): name of site ('gdrive' or specific user site)
        Returns:
            (int) - number of failed attempts
        """
        _, rec = self._get_site_rec(file.get("sites", []), provider)
        return rec.get("tries", 0)

    def _get_progress_dict(self, progress):
        """
            Provide progress metadata to be stored in Db.
            Used during upload/download for GUI to show.
        Args:
            progress: (float) - 0-1 progress of upload/download
        Returns:
            (dictionary)
        """
        val = {"files.$[f].sites.$[s].progress": progress}
        return val

    def _get_priority_dict(self, priority, file_id):
        """
            Provide priority metadata to be stored in Db.
            Used during upload/download for GUI to show.
        Args:
            priority: (int) - priority for file(s)
        Returns:
            (dictionary)
        """
        if file_id:
            str_key = "files.$[f].sites.$[s].priority"
        else:
            str_key = "files.$[].sites.$[s].priority"
        return {str_key: int(priority)}

    def _get_retries_arr(self, project_name):
        """
            Returns array with allowed values in 'tries' field. If repre
            contains these values, it means it was tried to be synchronized
            but failed. We try up to 'self.presets["retry_cnt"]' times before
            giving up and skipping representation.
        Returns:
            (list)
        """
        retry_cnt = self.sync_project_settings[project_name].\
            get("config")["retry_cnt"]
        arr = [i for i in range(int(retry_cnt))]
        arr.append(None)

        return arr

    def _get_roots_config(self, presets, project_name, site_name):
        """
            Returns configured root(s) for 'project_name' and 'site_name' from
            settings ('presets')
        """
        return presets[project_name]['sites'][site_name]['root']
