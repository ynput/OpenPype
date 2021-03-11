from pype.api import (
    Anatomy,
    get_project_settings,
    get_local_site_id)

import threading
import concurrent.futures
from concurrent.futures._base import CancelledError

from enum import Enum
from datetime import datetime

from .providers import lib
import os
from bson.objectid import ObjectId

from avalon.api import AvalonMongoDB
from .utils import time_function

import six
from pype.lib import PypeLogger
from .. import PypeModule, ITrayModule
from .providers.local_drive import LocalDriveHandler

if six.PY2:
    web = asyncio = STATIC_DIR = WebSocketAsync = None
else:
    import asyncio

log = PypeLogger().get_logger("SyncServer")


class SyncStatus(Enum):
    DO_NOTHING = 0
    DO_UPLOAD = 1
    DO_DOWNLOAD = 2


class SyncServer(PypeModule, ITrayModule):
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

    name = "sync_server"
    label = "Sync Server"

    def initialize(self, module_settings):
        """
            Called during Module Manager creation.

            Collects needed data, checks asyncio presence.
            Sets 'enabled' according to global settings for the module.
            Shouldnt be doing any initialization, thats a job for 'tray_init'
        """
        self.enabled = module_settings[self.name]["enabled"]
        if asyncio is None:
            raise AssertionError(
                "SyncServer module requires Python 3.5 or higher."
            )
        # some parts of code need to run sequentially, not in async
        self.lock = None
        self.connection = None  # connection to avalon DB to update state
        # settings for all enabled projects for sync
        self.sync_project_settings = None
        self.sync_server_thread = None  # asyncio requires new thread

        self.action_show_widget = None
        self._paused = False
        self._paused_projects = set()
        self._paused_representations = set()
        self._anatomies = {}

    """ Start of Public API """
    def add_site(self, collection, representation_id, site_name=None):
        """
            Adds new site to representation to be synced.

            'collection' must have synchronization enabled (globally or
            project only)

            Used as a API endpoint from outside applications (Loader etc)

            Args:
                collection (string): project name (must match DB)
                representation_id (string): MongoDB _id value
                site_name (string): name of configured and active site

            Returns:
                throws ValueError if any issue
        """
        if not self.get_sync_project_setting(collection):
            raise ValueError("Project not configured")

        if not site_name:
            site_name = self.DEFAULT_SITE

        self.reset_provider_for_file(collection,
                                     representation_id,
                                     site_name=site_name)

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

        return self._get_active_sites_from_settings(sync_settings)

    def get_active_site(self, project_name):
        """
            Returns active (mine) site for 'project_name' from settings

            Returns:
                (string)
        """
        active_site = self.get_sync_project_setting(project_name)['config']\
            ['active_site']
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
        return self.get_sync_project_setting(project_name)['config']\
            ['remote_site']

    """ End of Public API """

    def get_local_file_path(self, collection, file_path):
        """
            Externalized for app
        """
        local_file_path, _ = self._resolve_paths(file_path, collection)

        return local_file_path

    def _get_remote_sites_from_settings(self, sync_settings):
        if not self.enabled or not sync_settings['enabled']:
            return []

        remote_sites = [self.DEFAULT_SITE, self.LOCAL_SITE]
        if sync_settings:
            remote_sites.extend(sync_settings.get("sites").keys())

        return list(set(remote_sites))

    def _get_active_sites_from_settings(self, sync_settings):
        sites = [self.DEFAULT_SITE]
        if self.enabled and sync_settings['enabled']:
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
        if not self.enabled:
            return

        self.sync_project_settings = None
        self.lock = threading.Lock()

        self.connection = AvalonMongoDB()
        self.connection.install()

        try:
            self.set_sync_project_settings()
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
        action = QtWidgets.QAction("SyncServer", parent_menu)
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

    def set_sync_project_settings(self):
        """
            Set sync_project_settings for all projects (caching)

            For performance
        """
        sync_project_settings = {}
        if not self.connection:
            self.connection = AvalonMongoDB()
            self.connection.install()

        for collection in self.connection.database.collection_names(False):
            sync_settings = self._parse_sync_settings_from_settings(
                get_project_settings(collection))
            if sync_settings:
                default_sites = self._get_default_site_configs()
                sync_settings['sites'].update(default_sites)
                sync_project_settings[collection] = sync_settings

        if not sync_project_settings:
            log.info("No enabled and configured projects for sync.")

        self.sync_project_settings = sync_project_settings

    def get_sync_project_settings(self, refresh=False):
        """
            Collects all projects which have enabled syncing and their settings
        Args:
            refresh (bool): refresh presets from settings - used when user
                changes site in Local Settings or any time up-to-date values
                are necessary
        Returns:
            (dict): of settings, keys are project names
            {'projectA':{enabled: True, sites:{}...}
        """
        # presets set already, do not call again and again
        if refresh or not self.sync_project_settings:
            self.set_sync_project_settings()

        return self.sync_project_settings

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

    def site_is_working(self, project_name, site_name):
        """
            Confirm that 'site_name' is configured correctly for 'project_name'
            Args:
                project_name(string):
                site_name(string):
            Returns
                (bool)
        """
        if self._get_configured_sites(project_name).get(site_name):
            return True
        return False

    def _parse_sync_settings_from_settings(self, settings):
        """ settings from api.get_project_settings, TOOD rename """
        sync_settings = settings.get("global").get("sync_server")
        if not sync_settings:
            log.info("No project setting not syncing.")
            return {}
        if sync_settings.get("enabled"):
            return sync_settings

        return {}

    def _get_configured_sites(self, project_name):
        """
            Loops through settings and looks for configured sites and checks
            its handlers for particular 'project_name'.

            Args:
                project_setting(dict): dictionary from Settings
                only_project_name(string, optional): only interested in
                    particular project
            Returns:
                (dict of dict)
                {'ProjectA': {'studio':True, 'gdrive':False}}
        """
        settings = self.get_sync_project_setting(project_name)
        return self._get_configured_sites_from_setting(settings)

    def _get_configured_sites_from_setting(self, project_setting):
        if not project_setting.get("enabled"):
            return {}

        initiated_handlers = {}
        configured_sites = {}
        all_sites = self._get_default_site_configs()
        all_sites.update(project_setting.get("sites"))
        for site_name, config in all_sites.items():
            handler = initiated_handlers. \
                get((config["provider"], site_name))
            if not handler:
                handler = lib.factory.get_provider(config["provider"],
                                                   site_name,
                                                   presets=config)
                initiated_handlers[(config["provider"], site_name)] = \
                    handler

            if handler.is_active():
                configured_sites[site_name] = True

        return configured_sites

    def _get_default_site_configs(self):
        default_config = {'provider': 'local_drive'}
        all_sites = {self.DEFAULT_SITE: default_config,
                     self.LOCAL_SITE: default_config}
        return all_sites

    def get_provider_for_site(self, project_name, site):
        """
            Return provider name for site.
        """
        site_preset = self.get_sync_project_setting(project_name)["sites"].get(site)
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
        query = {
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
        log.debug("active_site:{} - remote_site:{}".format(active_site,
                                                           remote_site))
        log.debug("query: {}".format(query))
        representations = self.connection.find(query)

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

    async def upload(self, collection, file, representation, provider_name,
                     remote_site_name, tree=None, preset=None):
        """
            Upload single 'file' of a 'representation' to 'provider'.
            Source url is taken from 'file' portion, where {root} placeholder
            is replaced by 'representation.Context.root'
            Provider could be one of implemented in provider.py.

            Updates MongoDB, fills in id of file from provider (ie. file_id
            from GDrive), 'created_dt' - time of upload

            'provider_name' doesn't have to match to 'site_name', single
            provider (GDrive) might have multiple sites ('projectA',
            'projectB')

        Args:
            collection (str): source collection
            file (dictionary): of file from representation in Mongo
            representation (dictionary): of representation
            provider_name (string): gdrive, gdc etc.
            site_name (string): site on provider, single provider(gdrive) could
                have multiple sites (different accounts, credentials)
            tree (dictionary): injected memory structure for performance
            preset (dictionary): site config ('credentials_url', 'root'...)

        """
        # create ids sequentially, upload file in parallel later
        with self.lock:
            # this part modifies structure on 'remote_site', only single
            # thread can do that at a time, upload/download to prepared
            # structure should be run in parallel
            remote_handler = lib.factory.get_provider(provider_name,
                                                      remote_site_name,
                                                      tree=tree,
                                                      presets=preset)

            file_path = file.get("path", "")
            local_file_path, remote_file_path = self._resolve_paths(
                file_path, collection, remote_site_name, remote_handler
            )

            target_folder = os.path.dirname(remote_file_path)
            folder_id = remote_handler.create_folder(target_folder)

            if not folder_id:
                err = "Folder {} wasn't created. Check permissions.".\
                    format(target_folder)
                raise NotADirectoryError(err)

        loop = asyncio.get_running_loop()
        file_id = await loop.run_in_executor(None,
                                             remote_handler.upload_file,
                                             local_file_path,
                                             remote_file_path,
                                             self,
                                             collection,
                                             file,
                                             representation,
                                             remote_site_name,
                                             True
                                             )
        return file_id

    async def download(self, collection, file, representation, provider_name,
                       remote_site_name, tree=None, preset=None):
        """
            Downloads file to local folder denoted in representation.Context.

        Args:
         collection (str): source collection
         file (dictionary) : info about processed file
         representation (dictionary):  repr that 'file' belongs to
         provider_name (string):  'gdrive' etc
         site_name (string): site on provider, single provider(gdrive) could
                have multiple sites (different accounts, credentials)
         tree (dictionary): injected memory structure for performance
         preset (dictionary): site config ('credentials_url', 'root'...)

        Returns:
            (string) - 'name' of local file
        """
        with self.lock:
            remote_handler = lib.factory.get_provider(provider_name,
                                                      remote_site_name,
                                                      tree=tree,
                                                      presets=preset)

            file_path = file.get("path", "")
            local_file_path, remote_file_path = self._resolve_paths(
                file_path, collection, remote_site_name, remote_handler
            )

            local_folder = os.path.dirname(local_file_path)
            os.makedirs(local_folder, exist_ok=True)

        local_site = self.get_active_site(collection)

        loop = asyncio.get_running_loop()
        file_id = await loop.run_in_executor(None,
                                             remote_handler.download_file,
                                             remote_file_path,
                                             local_file_path,
                                             self,
                                             collection,
                                             file,
                                             representation,
                                             local_site,
                                             True
                                             )
        return file_id

    def update_db(self, collection, new_file_id, file, representation,
                  site, error=None, progress=None):
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

        Returns:
            None
        """
        representation_id = representation.get("_id")
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
        else:
            tries = self._get_tries_count(file, site)
            tries += 1

            update["$set"] = self._get_error_dict(error, tries)

        arr_filter = [
            {'s.name': site},
            {'f._id': ObjectId(file_id)}
        ]

        self.connection.database[collection].update_one(
            query,
            update,
            upsert=True,
            array_filters=arr_filter
        )

        if progress is not None:
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
                                remove=False, pause=None):
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
            self._add_site(collection, query, representation, elem, site_name)

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
        for file in representation.pop().get("files"):
            for site in file.get("sites"):
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
        for file in representation.pop().get("files"):
            for site in file.get("sites"):
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

    def _add_site(self, collection, query, representation, elem, site_name):
        """
            Adds 'site_name' to 'representation' on 'collection'

            Throws ValueError if already present
        """
        for file in representation.pop().get("files"):
            for site in file.get("sites"):
                if site["name"] == site_name:
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
        handler = lib.factory.get_provider(provider_name, site_name)

        if handler and isinstance(handler, LocalDriveHandler):
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
                local_file_path, _ = self._resolve_paths(file.get("path", ""),
                                                         collection
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

    def _resolve_paths(self, file_path, collection,
                       remote_site_name=None, remote_handler=None):
        """
            Returns tuple of local and remote file paths with {root}
            placeholders replaced with proper values from Settings or Anatomy

            Args:
                file_path(string): path with {root}
                collection(string): project name
                remote_site_name(string): remote site
                remote_handler(AbstractProvider): implementation
            Returns:
                (string, string) - proper absolute paths
        """
        remote_file_path = ''
        if remote_handler:
            root_configs = self._get_roots_config(self.sync_project_settings,
                                                  collection,
                                                  remote_site_name)

            remote_file_path = remote_handler.resolve_path(file_path,
                                                           root_configs)

        local_handler = lib.factory.get_provider(
            'local_drive', self.get_active_site(collection))
        local_file_path = local_handler.resolve_path(
            file_path, None, self.get_anatomy(collection))

        return local_file_path, remote_file_path

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


class SyncServerThread(threading.Thread):
    """
        Separate thread running synchronization server with asyncio loop.
        Stopped when tray is closed.
    """
    def __init__(self, module):
        super(SyncServerThread, self).__init__()
        self.module = module
        self.loop = None
        self.is_running = False
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)

    def run(self):
        self.is_running = True

        try:
            log.info("Starting Sync Server")
            self.loop = asyncio.new_event_loop()  # create new loop for thread
            asyncio.set_event_loop(self.loop)
            self.loop.set_default_executor(self.executor)

            asyncio.ensure_future(self.check_shutdown(), loop=self.loop)
            asyncio.ensure_future(self.sync_loop(), loop=self.loop)
            self.loop.run_forever()
        except Exception:
            log.warning(
                "Sync Server service has failed", exc_info=True
            )
        finally:
            self.loop.close()  # optional

    async def sync_loop(self):
        """
            Runs permanently, each time:
                - gets list of collections in DB
                - gets list of active remote providers (has configuration,
                    credentials)
                - for each collection it looks for representations that should
                    be synced
                - synchronize found collections
                - update representations - fills error messages for exceptions
                - waits X seconds and repeat
        Returns:

        """
        try:
            while self.is_running and not self.module.is_paused():
                import time
                start_time = None
                self.module.set_sync_project_settings()  # clean cache
                for collection, preset in self.module.get_sync_project_settings().\
                        items():
                    start_time = time.time()
                    local_site, remote_site = self._working_sites(collection)
                    if not all([local_site, remote_site]):
                        continue

                    sync_repres = self.module.get_sync_representations(
                        collection,
                        local_site,
                        remote_site
                    )

                    task_files_to_process = []
                    files_processed_info = []
                    # process only unique file paths in one batch
                    # multiple representation could have same file path
                    # (textures),
                    # upload process can find already uploaded file and
                    # reuse same id
                    processed_file_path = set()

                    site_preset = preset.get('sites')[remote_site]
                    remote_provider = site_preset['provider']
                    handler = lib.factory.get_provider(remote_provider,
                                                       remote_site,
                                                       presets=site_preset)
                    limit = lib.factory.get_provider_batch_limit(
                        site_preset['provider'])
                    # first call to get_provider could be expensive, its
                    # building folder tree structure in memory
                    # call only if needed, eg. DO_UPLOAD or DO_DOWNLOAD
                    for sync in sync_repres:
                        if self.module.\
                                is_representation_paused(sync['_id']):
                            continue
                        if limit <= 0:
                            continue
                        files = sync.get("files") or []
                        if files:
                            for file in files:
                                # skip already processed files
                                file_path = file.get('path', '')
                                if file_path in processed_file_path:
                                    continue
                                status = self.module.check_status(
                                    file,
                                    local_site,
                                    remote_site,
                                    preset.get('config'))
                                if status == SyncStatus.DO_UPLOAD:
                                    tree = handler.get_tree()
                                    limit -= 1
                                    task = asyncio.create_task(
                                        self.module.upload(collection,
                                                           file,
                                                           sync,
                                                           remote_provider,
                                                           remote_site,
                                                           tree,
                                                           site_preset))
                                    task_files_to_process.append(task)
                                    # store info for exception handlingy
                                    files_processed_info.append((file,
                                                                 sync,
                                                                 remote_site,
                                                                 collection
                                                                 ))
                                    processed_file_path.add(file_path)
                                if status == SyncStatus.DO_DOWNLOAD:
                                    tree = handler.get_tree()
                                    limit -= 1
                                    task = asyncio.create_task(
                                        self.module.download(collection,
                                                             file,
                                                             sync,
                                                             remote_provider,
                                                             remote_site,
                                                             tree,
                                                             site_preset))
                                    task_files_to_process.append(task)

                                    files_processed_info.append((file,
                                                                 sync,
                                                                 local_site,
                                                                 collection
                                                                 ))
                                    processed_file_path.add(file_path)

                    log.debug("Sync tasks count {}".
                              format(len(task_files_to_process)))
                    files_created = await asyncio.gather(
                        *task_files_to_process,
                        return_exceptions=True)
                    for file_id, info in zip(files_created,
                                             files_processed_info):
                        file, representation, site, collection = info
                        error = None
                        if isinstance(file_id, BaseException):
                            error = str(file_id)
                            file_id = None
                        self.module.update_db(collection,
                                              file_id,
                                              file,
                                              representation,
                                              site,
                                              error)

                duration = time.time() - start_time
                log.debug("One loop took {:.2f}s".format(duration))
                await asyncio.sleep(self.module.get_loop_delay(collection))
        except ConnectionResetError:
            log.warning("ConnectionResetError in sync loop, trying next loop",
                        exc_info=True)
        except CancelledError:
            # just stopping server
            pass
        except Exception:
            self.stop()
            log.warning("Unhandled exception in sync loop, stopping server",
                        exc_info=True)

    def stop(self):
        """Sets is_running flag to false, 'check_shutdown' shuts server down"""
        self.is_running = False

    async def check_shutdown(self):
        """ Future that is running and checks if server should be running
            periodically.
        """
        while self.is_running:
            await asyncio.sleep(0.5)
        tasks = [task for task in asyncio.all_tasks() if
                 task is not asyncio.current_task()]
        list(map(lambda task: task.cancel(), tasks))  # cancel all the tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        log.debug(f'Finished awaiting cancelled tasks, results: {results}...')
        await self.loop.shutdown_asyncgens()
        # to really make sure everything else has time to stop
        self.executor.shutdown(wait=True)
        await asyncio.sleep(0.07)
        self.loop.stop()

    def _working_sites(self, collection):
        if self.module.is_project_paused(collection):
            log.debug("Both sites same, skipping")
            return None, None

        local_site = self.module.get_active_site(collection)
        remote_site = self.module.get_remote_site(collection)
        if local_site == remote_site:
            log.debug("{}-{} sites same, skipping".format(local_site,
                                                          remote_site))
            return None, None

        if not all([self.module.site_is_working(collection, local_site),
                   self.module.site_is_working(collection, remote_site)]):
            log.debug("Some of the sites {} - {} is not ".format(local_site,
                                                                 remote_site) +
                      "working properly")
            return None, None

        return local_site, remote_site
