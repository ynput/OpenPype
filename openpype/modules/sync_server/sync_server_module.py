import os
import sys
import time
from datetime import datetime
import threading
import copy
import signal
from collections import deque, defaultdict

from bson.objectid import ObjectId

from openpype.client import (
    get_projects,
    get_representations,
    get_representation_by_id,
)
from openpype.modules import (
    OpenPypeModule,
    ITrayModule,
    IPluginPaths,
    click_wrap,
)
from openpype.settings import (
    get_project_settings,
    get_system_settings,
)
from openpype.lib import Logger, get_local_site_id
from openpype.pipeline import AvalonMongoDB, Anatomy
from openpype.settings.lib import (
    get_default_anatomy_settings,
    get_anatomy_settings,
    get_local_settings,
)
from openpype.settings.constants import (
    DEFAULT_PROJECT_KEY
)

from .providers.local_drive import LocalDriveHandler
from .providers import lib

from .utils import (
    time_function,
    SyncStatus,
    SiteAlreadyPresentError,
    SYNC_SERVER_ROOT,
)

log = Logger.get_logger("SyncServer")


class SyncServerModule(OpenPypeModule, ITrayModule, IPluginPaths):
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
        self._sync_system_settings = None
        # settings for all enabled projects for sync
        self._sync_project_settings = None
        self.sync_server_thread = None  # asyncio requires new thread

        self.action_show_widget = None
        self._paused = False
        self._paused_projects = set()
        self._anatomies = {}

        self._connection = None

        # list of long blocking tasks
        self.long_running_tasks = deque()
        # projects that long tasks are running on
        self.projects_processed = set()

    def get_plugin_paths(self):
        """Deadline plugin paths."""
        return {
            "load": [os.path.join(SYNC_SERVER_ROOT, "plugins", "load")]
        }

    def get_site_icons(self):
        """Icons for sites.

        Returns:
            dict[str, str]: Path to icon by site.
        """

        resource_path = os.path.join(
            SYNC_SERVER_ROOT, "providers", "resources"
        )
        return {
            provider: "{}/{}.png".format(resource_path, provider)
            for provider in ["studio", "local_drive", "gdrive"]
        }

    """ Start of Public API """
    def add_site(self, project_name, representation_id, site_name=None,
                 force=False, priority=None, reset_timer=False):
        """
        Adds new site to representation to be synced.

        'project_name' must have synchronization enabled (globally or
        project only)

        Used as an API endpoint from outside applications (Loader etc).

        Use 'force' to reset existing site.

        Args:
            project_name (string): project name (must match DB)
            representation_id (string): MongoDB _id value
            site_name (string): name of configured and active site
            force (bool): reset site if exists
            priority (int): set priority
            reset_timer (bool): if delay timer should be reset, eg. user mark
                some representation to be synced manually

        Throws:
            SiteAlreadyPresentError - if adding already existing site and
                not 'force'
            ValueError - other errors (repre not found, misconfiguration)
        """
        if not self.get_sync_project_setting(project_name):
            raise ValueError("Project not configured")

        if not site_name:
            site_name = self.DEFAULT_SITE

        self.reset_site_on_representation(project_name,
                                          representation_id,
                                          site_name=site_name,
                                          force=force,
                                          priority=priority)

        if reset_timer:
            self.reset_timer()

    def remove_site(self, project_name, representation_id, site_name,
                    remove_local_files=False):
        """
            Removes 'site_name' for particular 'representation_id' on
            'project_name'

            Args:
                project_name (string): project name (must match DB)
                representation_id (string): MongoDB _id value
                site_name (string): name of configured and active site
                remove_local_files (bool): remove only files for 'local_id'
                    site

            Returns:
                throws ValueError if any issue
        """
        if not self.get_sync_project_setting(project_name):
            raise ValueError("Project not configured")

        self.reset_site_on_representation(project_name,
                                          representation_id,
                                          site_name=site_name,
                                          remove=True)
        if remove_local_files:
            self._remove_local_file(project_name, representation_id, site_name)

    def get_progress_for_repre(self, doc, active_site, remote_site):
        """
            Calculates average progress for representation.
            If site has created_dt >> fully available >> progress == 1
            Could be calculated in aggregate if it would be too slow
            Args:
                doc(dict): representation dict
            Returns:
                (dict) with active and remote sites progress
                {'studio': 1.0, 'gdrive': -1} - gdrive site is not present
                    -1 is used to highlight the site should be added
                {'studio': 1.0, 'gdrive': 0.0} - gdrive site is present, not
                    uploaded yet
        """
        progress = {active_site: -1,
                    remote_site: -1}
        if not doc:
            return progress

        files = {active_site: 0, remote_site: 0}
        doc_files = doc.get("files") or []
        for doc_file in doc_files:
            if not isinstance(doc_file, dict):
                continue

            sites = doc_file.get("sites") or []
            for site in sites:
                if (
                        # Pype 2 compatibility
                        not isinstance(site, dict)
                        # Check if site name is one of progress sites
                        or site["name"] not in progress
                ):
                    continue

                files[site["name"]] += 1
                norm_progress = max(progress[site["name"]], 0)
                if site.get("created_dt"):
                    progress[site["name"]] = norm_progress + 1
                elif site.get("progress"):
                    progress[site["name"]] = norm_progress + site["progress"]
                else:  # site exists, might be failed, do not add again
                    progress[site["name"]] = 0

        # for example 13 fully avail. files out of 26 >> 13/26 = 0.5
        avg_progress = {}
        avg_progress[active_site] = \
            progress[active_site] / max(files[active_site], 1)
        avg_progress[remote_site] = \
            progress[remote_site] / max(files[remote_site], 1)
        return avg_progress

    def compute_resource_sync_sites(self, project_name):
        """Get available resource sync sites state for publish process.

        Returns dict with prepared state of sync sites for 'project_name'.
        It checks if Site Sync is enabled, handles alternative sites.
        Publish process stores this dictionary as a part of representation
        document in DB.

        Example:
        [
            {
                'name': '42abbc09-d62a-44a4-815c-a12cd679d2d7',
                'created_dt': datetime.datetime(2022, 3, 30, 12, 16, 9, 778637)
            },
            {'name': 'studio'},
            {'name': 'SFTP'}
        ] -- representation is published locally, artist or Settings have set
        remote site as 'studio'. 'SFTP' is alternate site to 'studio'. Eg.
        whenever file is on 'studio', it is also on 'SFTP'.
        """

        def create_metadata(name, created=True):
            """Create sync site metadata for site with `name`"""
            metadata = {"name": name}
            if created:
                metadata["created_dt"] = datetime.now()
            return metadata

        if (
                not self.sync_system_settings["enabled"] or
                not self.sync_project_settings[project_name]["enabled"]):
            return [create_metadata(self.DEFAULT_SITE)]

        local_site = self.get_active_site(project_name)
        remote_site = self.get_remote_site(project_name)

        # Attached sites metadata by site name
        # That is the local site, remote site, the always accesible sites
        # and their alternate sites (alias of sites with different protocol)
        attached_sites = dict()
        attached_sites[local_site] = create_metadata(local_site)

        if remote_site and remote_site not in attached_sites:
            attached_sites[remote_site] = create_metadata(remote_site,
                                                          created=False)

        attached_sites = self._add_alternative_sites(attached_sites)
        # add skeleton for sites where it should be always synced to
        # usually it would be a backup site which is handled by separate
        # background process
        for site in self._get_always_accessible_sites(project_name):
            if site not in attached_sites:
                attached_sites[site] = create_metadata(site, created=False)

        return list(attached_sites.values())

    def _get_always_accessible_sites(self, project_name):
        """Sites that synced to as a part of background process.

        Artist machine doesn't handle those, explicit Tray with that site name
        as a local id must be running.
        Example is dropbox site serving as a backup solution
        """
        always_accessible_sites = (
            self.get_sync_project_setting(project_name)["config"].
            get("always_accessible_on", [])
        )
        return [site.strip() for site in always_accessible_sites]

    def _add_alternative_sites(self, attached_sites):
        """Add skeleton document for alternative sites

        Each new configured site in System Setting could serve as a alternative
        site, it's a kind of alias. It means that files on 'a site' are
        physically accessible also on 'a alternative' site.
        Example is sftp site serving studio files via sftp protocol, physically
        file is only in studio, sftp server has this location mounted.
        """
        additional_sites = self.sync_system_settings.get("sites", {})

        alt_site_pairs = self._get_alt_site_pairs(additional_sites)

        for site_name in additional_sites.keys():
            # Get alternate sites (stripped names) for this site name
            alt_sites = alt_site_pairs.get(site_name)
            alt_sites = [site.strip() for site in alt_sites]
            alt_sites = set(alt_sites)

            # If no alternative sites we don't need to add
            if not alt_sites:
                continue

            # Take a copy of data of the first alternate site that is already
            # defined as an attached site to match the same state.
            match_meta = next((attached_sites[site] for site in alt_sites
                               if site in attached_sites), None)
            if not match_meta:
                continue

            alt_site_meta = copy.deepcopy(match_meta)
            alt_site_meta["name"] = site_name

            # Note: We change mutable `attached_site` dict in-place
            attached_sites[site_name] = alt_site_meta

        return attached_sites

    def _get_alt_site_pairs(self, conf_sites):
        """Returns dict of site and its alternative sites.

        If `site` has alternative site, it means that alt_site has 'site' as
        alternative site
        Args:
            conf_sites (dict)
        Returns:
            (dict): {'site': [alternative sites]...}
        """
        alt_site_pairs = defaultdict(set)
        for site_name, site_info in conf_sites.items():
            alt_sites = set(site_info.get("alternative_sites", []))
            alt_site_pairs[site_name].update(alt_sites)

            for alt_site in alt_sites:
                alt_site_pairs[alt_site].add(site_name)

        for site_name, alt_sites in alt_site_pairs.items():
            sites_queue = deque(alt_sites)
            while sites_queue:
                alt_site = sites_queue.popleft()

                # safety against wrong config
                # {"SFTP": {"alternative_site": "SFTP"}
                if alt_site == site_name or alt_site not in alt_site_pairs:
                    continue

                for alt_alt_site in alt_site_pairs[alt_site]:
                    if (
                            alt_alt_site != site_name
                            and alt_alt_site not in alt_sites
                    ):
                        alt_sites.add(alt_alt_site)
                        sites_queue.append(alt_alt_site)

        return alt_site_pairs

    def clear_project(self, project_name, site_name):
        """
            Clear 'project_name' of 'site_name' and its local files

            Works only on real local sites, not on 'studio'
        """
        query = {
            "type": "representation",
            "files.sites.name": site_name
        }

        # TODO currently not possible to replace with get_representations
        representations = list(
            self.connection.database[project_name].find(query))
        if not representations:
            self.log.debug("No repre found")
            return

        for repre in representations:
            self.remove_site(project_name, repre.get("_id"), site_name, True)

    def create_validate_project_task(self, project_name, site_name):
        """Adds metadata about project files validation on a queue.

        This process will loop through all representation and check if
        their files actually exist on an active site.

        It also checks if site is set in DB, but file is physically not
        present

        This might be useful for edge cases when artists is switching
        between sites, remote site is actually physically mounted and
        active site has same file urls etc.

        Task will run on a asyncio loop, shouldn't be blocking.
        """
        task = {
            "type": "validate",
            "project_name": project_name,
            "func": lambda: self.validate_project(project_name, site_name,
                                                  reset_missing=True)
        }
        self.projects_processed.add(project_name)
        self.long_running_tasks.append(task)

    def validate_project(self, project_name, site_name, reset_missing=False):
        """Validate 'project_name' of 'site_name' and its local files

        If file present and not marked with a 'site_name' in DB, DB is
        updated with site name and file modified date.

        Args:
            project_name (string): project name
            site_name (string): active site name
            reset_missing (bool): if True reset site in DB if missing
                physically
        """
        self.log.debug("Validation of {} for {} started".format(project_name,
                                                                site_name))
        representations = list(get_representations(project_name))
        if not representations:
            self.log.debug("No repre found")
            return

        sites_added = 0
        sites_reset = 0
        for repre in representations:
            repre_id = repre["_id"]
            for repre_file in repre.get("files", []):
                try:
                    is_on_site = site_name in [site["name"]
                                               for site in repre_file["sites"]
                                               if (site.get("created_dt") and
                                               not site.get("error"))]
                except (TypeError, AttributeError):
                    self.log.debug("Structure error in {}".format(repre_id))
                    continue

                file_path = repre_file.get("path", "")
                local_file_path = self.get_local_file_path(project_name,
                                                           site_name,
                                                           file_path)

                file_exists = (local_file_path and
                               os.path.exists(local_file_path))
                if not is_on_site:
                    if file_exists:
                        self.log.debug(
                            "Adding site {} for {}".format(site_name,
                                                           repre_id))

                        created_dt = datetime.fromtimestamp(
                            os.path.getmtime(local_file_path))
                        elem = {"name": site_name,
                                "created_dt": created_dt}
                        self._add_site(project_name, repre, elem,
                                       site_name=site_name,
                                       file_id=repre_file["_id"],
                                       force=True)
                        sites_added += 1
                else:
                    if not file_exists and reset_missing:
                        self.log.debug("Resetting site {} for {}".
                                       format(site_name, repre_id))
                        self.reset_site_on_representation(
                            project_name, repre_id, site_name=site_name,
                            file_id=repre_file["_id"])
                        sites_reset += 1

        if sites_added % 100 == 0:
            self.log.debug("Sites added {}".format(sites_added))

        self.log.debug("Validation of {} for {} ended".format(project_name,
                                                              site_name))
        self.log.info("Sites added {}, sites reset {}".format(sites_added,
                                                              reset_missing))

    def pause_representation(self, project_name, representation_id, site_name):
        """
            Sets 'representation_id' as paused, eg. no syncing should be
            happening on it.

            Args:
                project_name (string): project name
                representation_id (string): MongoDB objectId value
                site_name (string): 'gdrive', 'studio' etc.
        """
        self.log.info("Pausing SyncServer for {}".format(representation_id))
        self.reset_site_on_representation(project_name, representation_id,
                                          site_name=site_name, pause=True)

    def unpause_representation(self, project_name,
                               representation_id, site_name):
        """
            Sets 'representation_id' as unpaused.

            Does not fail or warn if repre wasn't paused.

            Args:
                project_name (string): project name
                representation_id (string): MongoDB objectId value
                site_name (string): 'gdrive', 'studio' etc.
        """
        self.log.info("Unpausing SyncServer for {}".format(representation_id))
        self.reset_site_on_representation(project_name, representation_id,
                                          site_name=site_name, pause=False)

    def is_representation_paused(self, project_name, representation_id,
                                 site_name, check_parents=False):
        """
            Returns if 'representation_id' is paused or not for site.

            Args:
                project_name (str): project to check if paused
                representation_id (str): MongoDB objectId value
                site (str): site to check representation is paused for
                check_parents (bool): check if parent project or server itself
                    are not paused

            Returns:
                (bool)
        """
        # Check parents are paused
        if check_parents and (
            self.is_project_paused(project_name)
            or self.is_paused()
        ):
            return True

        # Get representation
        representation = get_representation_by_id(project_name,
                                                  representation_id,
                                                  fields=["files.sites"])
        if not representation:
            return False

        # Check if representation is paused
        for file_info in representation.get("files", []):
            for site in file_info.get("sites", []):
                if site["name"] != site_name:
                    continue

                return site.get("paused", False)

        return False

    def pause_project(self, project_name):
        """
            Sets 'project_name' as paused, eg. no syncing should be
            happening on all representation inside.

            Args:
                project_name (string): project_name name
        """
        self.log.info("Pausing SyncServer for {}".format(project_name))
        self._paused_projects.add(project_name)

    def unpause_project(self, project_name):
        """
            Sets 'project_name' as unpaused

            Does not fail or warn if project wasn't paused.

            Args:
                project_name (string):
        """
        self.log.info("Unpausing SyncServer for {}".format(project_name))
        try:
            self._paused_projects.remove(project_name)
        except KeyError:
            pass

    def is_project_paused(self, project_name, check_parents=False):
        """
            Returns if 'project_name' is paused or not.

            Args:
                project_name (string):
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
        self.log.info("Pausing SyncServer")
        self._paused = True

    def unpause_server(self):
        """
            Unpause server
        """
        self.log.info("Unpausing SyncServer")
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

    def get_active_site_type(self, project_name, local_settings=None):
        """Active site which is defined by artist.

        Unlike 'get_active_site' is this method also checking local settings
        where might be different active site set by user. The output is limited
        to "studio" and "local".

        This method is used by Anatomy when is decided which

        Todos:
            Check if sync server is enabled for the project.
            - To be able to do that the sync settings MUST NOT be cached for
                all projects at once. The sync settings preparation for all
                projects is reasonable only in sync server loop.

        Args:
            project_name (str): Name of project where to look for active site.
            local_settings (Optional[dict[str, Any]]): Prepared local settings.

        Returns:
            Literal["studio", "local"]: Active site.
        """

        if not self.enabled:
            return "studio"

        if local_settings is None:
            local_settings = get_local_settings()

        local_project_settings = local_settings.get("projects")
        project_settings = get_project_settings(project_name)
        sync_server_settings = project_settings["global"]["sync_server"]
        if not sync_server_settings["enabled"]:
            return "studio"

        project_active_site = sync_server_settings["config"]["active_site"]
        if not local_project_settings:
            return project_active_site

        project_locals = local_project_settings.get(project_name) or {}
        default_locals = local_project_settings.get(DEFAULT_PROJECT_KEY) or {}
        active_site = (
            project_locals.get("active_site")
            or default_locals.get("active_site")
        )
        if active_site:
            return active_site
        return project_active_site

    def get_site_root_overrides(
        self, project_name, site_name, local_settings=None
    ):
        """Get root overrides for project on a site.

        Implemented to be used in 'Anatomy' for other than 'studio' site.

        Args:
            project_name (str): Project for which root overrides should be
                received.
            site_name (str): Name of site for which should be received roots.
            local_settings (Optional[dict[str, Any]]): Prepare local settigns
                values.

        Returns:
            Union[dict[str, Any], None]: Root overrides for this machine.
        """

        # Validate that site name is valid
        if site_name not in ("studio", "local"):
            # Considure local site id as 'local'
            if site_name != get_local_site_id():
                raise ValueError((
                    "Root overrides are available only for"
                    " default sites not for \"{}\""
                ).format(site_name))
            site_name = "local"

        if local_settings is None:
            local_settings = get_local_settings()

        if not local_settings:
            return

        local_project_settings = local_settings.get("projects") or {}

        # Check for roots existence in local settings first
        roots_project_locals = (
            local_project_settings
            .get(project_name, {})
        )
        roots_default_locals = (
            local_project_settings
            .get(DEFAULT_PROJECT_KEY, {})
        )

        # Skip rest of processing if roots are not set
        if not roots_project_locals and not roots_default_locals:
            return

        # Combine roots from local settings
        roots_locals = roots_default_locals.get(site_name) or {}
        roots_locals.update(roots_project_locals.get(site_name) or {})
        return roots_locals

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

    def get_local_normalized_site(self, site_name):
        """
            Return 'site_name' or 'local' if 'site_name' is local id.

            In some places Settings or Local Settings require 'local' instead
            of real site name.
        """
        if site_name == get_local_site_id():
            site_name = self.LOCAL_SITE

        return site_name

    # Methods for Settings UI to draw appropriate forms
    @classmethod
    def get_system_settings_schema(cls):
        """ Gets system level schema of  configurable items

            Used for Setting UI to provide forms.
        """
        ret_dict = {}
        for provider_code in lib.factory.providers:
            ret_dict[provider_code] = \
                lib.factory.get_provider_cls(provider_code). \
                get_system_settings_schema()

        return ret_dict

    @classmethod
    def get_project_settings_schema(cls):
        """ Gets project level schema of configurable items.

            It is not using Setting! Used for Setting UI to provide forms.
        """
        ret_dict = {}
        for provider_code in lib.factory.providers:
            ret_dict[provider_code] = \
                lib.factory.get_provider_cls(provider_code). \
                get_project_settings_schema()

        return ret_dict

    @classmethod
    def get_local_settings_schema(cls):
        """ Gets local level schema of configurable items.

            It is not using Setting! Used for Setting UI to provide forms.
        """
        ret_dict = {}
        for provider_code in lib.factory.providers:
            ret_dict[provider_code] = \
                lib.factory.get_provider_cls(provider_code). \
                get_local_settings_schema()

        return ret_dict

    def get_launch_hook_paths(self):
        """Implementation for applications launch hooks.

        Returns:
            (str): full absolut path to directory with hooks for the module
        """

        return os.path.join(SYNC_SERVER_ROOT, "launch_hooks")

    # Needs to be refactored after Settings are updated
    # # Methods for Settings to get appriate values to fill forms
    # def get_configurable_items(self, scope=None):
    #     """
    #         Returns list of sites that could be configurable for all projects
    #
    #         Could be filtered by 'scope' argument (list)
    #
    #         Args:
    #             scope (list of utils.EditableScope)
    #
    #         Returns:
    #             (dict of list of dict)
    #             {
    #                 siteA : [
    #                     {
    #                         key:"root", label:"root",
    #                         "value":"{'work': 'c:/projects'}",
    #                         "type": "dict",
    #                         "children":[
    #                             { "key": "work",
    #                               "type": "text",
    #                               "value": "c:/projects"}
    #                         ]
    #                     },
    #                     {
    #                         key:"credentials_url", label:"Credentials url",
    #                         "value":"'c:/projects/cred.json'", "type": "text",  # noqa: E501
    #                         "namespace": "{project_setting}/global/sync_server/  # noqa: E501
    #                                  sites"
    #                     }
    #                 ]
    #             }
    #     """
    #     editable = {}
    #     applicable_projects = list(self.connection.projects())
    #     applicable_projects.append(None)
    #     for project in applicable_projects:
    #         project_name = None
    #         if project:
    #             project_name = project["name"]
    #
    #         items = self.get_configurable_items_for_project(project_name,
    #                                                         scope)
    #         editable.update(items)
    #
    #     return editable
    #
    # def get_local_settings_schema_for_project(self, project_name):
    #     """Wrapper for Local settings - for specific 'project_name'"""
    #     return self.get_configurable_items_for_project(project_name,
    #                                                    EditableScopes.LOCAL)
    #
    # def get_configurable_items_for_project(self, project_name=None,
    #                                        scope=None):
    #     """
    #         Returns list of items that could be configurable for specific
    #         'project_name'
    #
    #         Args:
    #             project_name (str) - None > default project,
    #             scope (list of utils.EditableScope)
    #                 (optional, None is all scopes, default is LOCAL)
    #
    #         Returns:
    #             (dict of list of dict)
    #         {
    #             siteA : [
    #                 {
    #                     key:"root", label:"root",
    #                     "type": "dict",
    #                     "children":[
    #                         { "key": "work",
    #                           "type": "text",
    #                           "value": "c:/projects"}
    #                     ]
    #                 },
    #                 {
    #                     key:"credentials_url", label:"Credentials url",
    #                     "value":"'c:/projects/cred.json'", "type": "text",
    #                     "namespace": "{project_setting}/global/sync_server/
    #                                  sites"
    #                 }
    #             ]
    #         }
    #     """
    #     allowed_sites = set()
    #     sites = self.get_all_site_configs(project_name)
    #     if project_name:
    #         # Local Settings can select only from allowed sites for project
    #         allowed_sites.update(set(self.get_active_sites(project_name)))
    #         allowed_sites.update(set(self.get_remote_sites(project_name)))
    #
    #     editable = {}
    #     for site_name in sites.keys():
    #         if allowed_sites and site_name not in allowed_sites:
    #             continue
    #
    #         items = self.get_configurable_items_for_site(project_name,
    #                                                      site_name,
    #                                                      scope)
    #         # Local Settings need 'local' instead of real value
    #         site_name = site_name.replace(get_local_site_id(), 'local')
    #         editable[site_name] = items
    #
    #     return editable
    #
    # def get_configurable_items_for_site(self, project_name=None,
    #                                     site_name=None,
    #                                     scope=None):
    #     """
    #         Returns list of items that could be configurable.
    #
    #         Args:
    #             project_name (str) - None > default project
    #             site_name (str)
    #             scope (list of utils.EditableScope)
    #                 (optional, None is all scopes)
    #
    #         Returns:
    #             (list)
    #             [
    #                 {
    #                     key:"root", label:"root", type:"dict",
    #                     "children":[
    #                         { "key": "work",
    #                           "type": "text",
    #                           "value": "c:/projects"}
    #                     ]
    #                 }, ...
    #             ]
    #     """
    #     provider_name = self.get_provider_for_site(site=site_name)
    #     items = lib.factory.get_provider_configurable_items(provider_name)
    #
    #     if project_name:
    #         sync_s = self.get_sync_project_setting(project_name,
    #                                                exclude_locals=True,
    #                                                cached=False)
    #     else:
    #         sync_s = get_default_project_settings(exclude_locals=True)
    #         sync_s = sync_s["global"]["sync_server"]
    #         sync_s["sites"].update(
    #             self._get_default_site_configs(self.enabled))
    #
    #     editable = []
    #     if type(scope) is not list:
    #         scope = [scope]
    #     scope = set(scope)
    #     for key, properties in items.items():
    #         if scope is None or scope.intersection(set(properties["scope"])):
    #             val = sync_s.get("sites", {}).get(site_name, {}).get(key)
    #
    #             item = {
    #                 "key": key,
    #                 "label": properties["label"],
    #                 "type": properties["type"]
    #             }
    #
    #             if properties.get("namespace"):
    #                 item["namespace"] = properties.get("namespace")
    #                 if "platform" in item["namespace"]:
    #                     try:
    #                         if val:
    #                             val = val[platform.system().lower()]
    #                     except KeyError:
    #                         st = "{}'s field value {} should be".format(key, val)  # noqa: E501
    #                         self.log.error(st + " multiplatform dict")
    #
    #                 item["namespace"] = item["namespace"].replace('{site}',
    #                                                               site_name)
    #             children = []
    #             if properties["type"] == "dict":
    #                 if val:
    #                     for val_key, val_val in val.items():
    #                         child = {
    #                             "type": "text",
    #                             "key": val_key,
    #                             "value": val_val
    #                         }
    #                         children.append(child)
    #
    #             if properties["type"] == "dict":
    #                 item["children"] = children
    #             else:
    #                 item["value"] = val
    #
    #             editable.append(item)
    #
    #     return editable

    def reset_timer(self):
        """
            Called when waiting for next loop should be skipped.

            In case of user's involvement (reset site), start that right away.
        """

        if not self.enabled:
            return

        if self.sync_server_thread is None:
            self._reset_timer_with_rest_api()
        else:
            self.sync_server_thread.reset_timer()

    def is_representation_on_site(
        self, project_name, representation_id, site_name, max_retries=None
    ):
        """Checks if 'representation_id' has all files avail. on 'site_name'

        Args:
            project_name (str)
            representation_id (str)
            site_name (str)
            max_retries (int) (optional) - provide only if method used in while
                loop to bail out
        Returns:
            (bool): True if 'representation_id' has all files correctly on the
            'site_name'
        Raises:
              (ValueError)  Only If 'max_retries' provided if upload/download
        failed too many times to limit infinite loop check.
        """
        representation = get_representation_by_id(project_name,
                                                  representation_id,
                                                  fields=["_id", "files"])
        if not representation:
            return False

        on_site = False
        for file_info in representation.get("files", []):
            for site in file_info.get("sites", []):
                if site["name"] != site_name:
                    continue

                if max_retries:
                    tries = self._get_tries_count_from_rec(site)
                    if tries >= max_retries:
                        raise ValueError("Failed too many times")

                if (site.get("progress") or site.get("error") or
                        not site.get("created_dt")):
                    return False
                on_site = True

        return on_site

    def _reset_timer_with_rest_api(self):
        # POST to webserver sites to add to representations
        webserver_url = os.environ.get("OPENPYPE_WEBSERVER_URL")
        if not webserver_url:
            self.log.warning("Couldn't find webserver url")
            return

        rest_api_url = "{}/sync_server/reset_timer".format(
            webserver_url
        )

        try:
            import requests
        except Exception:
            self.log.warning(
                "Couldn't add sites to representations "
                "('requests' is not available)"
            )
            return

        requests.post(rest_api_url)

    def get_enabled_projects(self):
        """Returns list of projects which have SyncServer enabled."""
        enabled_projects = []

        if self.enabled:
            for project in get_projects(fields=["name"]):
                project_name = project["name"]
                if self.is_project_enabled(project_name):
                    enabled_projects.append(project_name)

        return enabled_projects

    def is_project_enabled(self, project_name, single=False):
        """Checks if 'project_name' is enabled for syncing.
        'get_sync_project_setting' is potentially expensive operation (pulls
        settings for all projects if cached version is not available), using
        project_settings for specific project should be faster.
        Args:
            project_name (str)
            single (bool): use 'get_project_settings' method
        """
        if self.enabled:
            if single:
                project_settings = get_project_settings(project_name)
                project_settings = \
                    self._parse_sync_settings_from_settings(project_settings)
            else:
                project_settings = self.get_sync_project_setting(project_name)
            if project_settings and project_settings.get("enabled"):
                return True
        return False

    def handle_alternate_site(self, project_name, representation,
                              processed_site, file_id, synced_file_id):
        """
            For special use cases where one site vendors another.

            Current use case is sftp site vendoring (exposing) same data as
            regular site (studio). Each site is accessible for different
            audience. 'studio' for artists in a studio, 'sftp' for externals.

            Change of file status on one site actually means same change on
            'alternate' site. (eg. artists publish to 'studio', 'sftp' is using
            same location >> file is accesible on 'sftp' site right away.

            Args:
                project_name (str): name of project
                representation (dict)
                processed_site (str): real site_name of published/uploaded file
                file_id (ObjectId): DB id of file handled
                synced_file_id (str): id of the created file returned
                    by provider
        """
        sites = self.sync_system_settings.get("sites", {})
        sites[self.DEFAULT_SITE] = {"provider": "local_drive",
                                    "alternative_sites": []}

        alternate_sites = []
        for site_name, site_info in sites.items():
            conf_alternative_sites = site_info.get("alternative_sites", [])
            if processed_site in conf_alternative_sites:
                alternate_sites.append(site_name)
                continue
            if processed_site == site_name and conf_alternative_sites:
                alternate_sites.extend(conf_alternative_sites)
                continue

        alternate_sites = set(alternate_sites)

        for alt_site in alternate_sites:
            elem = {"name": alt_site,
                    "created_dt": datetime.now(),
                    "id": synced_file_id}

            self.log.debug("Adding alternate {} to {}".format(
                alt_site, representation["_id"]))
            self._add_site(project_name,
                           representation, elem,
                           alt_site, file_id=file_id, force=True)

    def get_repre_info_for_versions(self, project_name, version_ids,
                                    active_site, remote_site):
        """Returns representation documents for versions and sites combi

        Args:
            project_name (str)
            version_ids (list): of version[_id]
            active_site (string): 'local', 'studio' etc
            remote_site (string): dtto
        Returns:

        """
        self.connection.Session["AVALON_PROJECT"] = project_name
        query = [
            {"$match": {"parent": {"$in": version_ids},
                        "type": "representation",
                        "files.sites.name": {"$exists": 1}}},
            {"$unwind": "$files"},
            {'$addFields': {
                'order_local': {
                    '$filter': {
                        'input': '$files.sites', 'as': 'p',
                        'cond': {'$eq': ['$$p.name', active_site]}
                    }
                }
            }},
            {'$addFields': {
                'order_remote': {
                    '$filter': {
                        'input': '$files.sites', 'as': 'p',
                        'cond': {'$eq': ['$$p.name', remote_site]}
                    }
                }
            }},
            {'$addFields': {
                'progress_local': {"$arrayElemAt": [{
                    '$cond': [
                        {'$size': "$order_local.progress"},
                        "$order_local.progress",
                        # if exists created_dt count is as available
                        {'$cond': [
                            {'$size': "$order_local.created_dt"},
                            [1],
                            [0]
                        ]}
                    ]},
                    0
                ]}
            }},
            {'$addFields': {
                'progress_remote': {"$arrayElemAt": [{
                    '$cond': [
                        {'$size': "$order_remote.progress"},
                        "$order_remote.progress",
                        # if exists created_dt count is as available
                        {'$cond': [
                            {'$size': "$order_remote.created_dt"},
                            [1],
                            [0]
                        ]}
                    ]},
                    0
                ]}
            }},
            {'$group': {  # first group by repre
                '_id': '$_id',
                'parent': {'$first': '$parent'},
                'avail_ratio_local': {
                    '$first': {
                        '$divide': [{'$sum': "$progress_local"}, {'$sum': 1}]
                    }
                },
                'avail_ratio_remote': {
                    '$first': {
                        '$divide': [{'$sum': "$progress_remote"}, {'$sum': 1}]
                    }
                }
            }},
            {'$group': {  # second group by parent, eg version_id
                '_id': '$parent',
                'repre_count': {'$sum': 1},  # total representations
                # fully available representation for site
                'avail_repre_local': {'$sum': "$avail_ratio_local"},
                'avail_repre_remote': {'$sum': "$avail_ratio_remote"},
            }},
        ]
        # docs = list(self.connection.aggregate(query))
        return self.connection.aggregate(query)

    """ End of Public API """

    def get_local_file_path(self, project_name, site_name, file_path):
        """
            Externalized for app
        """
        handler = LocalDriveHandler(project_name, site_name)
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

        active_site = sync_settings["config"]["active_site"]
        # for Tray running background process
        if active_site not in sites and active_site == get_local_site_id():
            sites.append(active_site)

        return sites

    def tray_init(self):
        """
            Actual initialization of Sync Server for Tray.

            Called when tray is initialized, it checks if module should be
            enabled. If not, no initialization necessary.
        """
        self.server_init()

    def server_init(self):
        """Actual initialization of Sync Server."""
        # import only in tray or Python3, because of Python2 hosts
        if not self.enabled:
            return

        from .sync_server import SyncServerThread

        self.lock = threading.Lock()

        self.sync_server_thread = SyncServerThread(self)

    def tray_start(self):
        """
            Triggered when Tray is started.

            Checks if configuration presets are available and if there is
            any provider ('gdrive', 'S3') that is activated
            (eg. has valid credentials).

        Returns:
            None
        """
        self.server_start()

    def server_start(self):
        if self.enabled:
            self.sync_server_thread.start()
        else:
            self.log.info("No presets or active providers. " +
                     "Synchronization not possible.")

    def tray_exit(self):
        """
            Stops sync thread if running.

            Called from Module Manager
        """
        self.server_exit()

    def server_exit(self):
        if not self.sync_server_thread:
            return

        if not self.is_running:
            return
        try:
            self.log.info("Stopping sync server server")
            self.sync_server_thread.is_running = False
            self.sync_server_thread.stop()
            self.log.info("Sync server stopped")
        except Exception:
            self.log.warning(
                "Error has happened during Killing sync server",
                exc_info=True
            )

    def tray_menu(self, parent_menu):
        if not self.enabled:
            return

        from qtpy import QtWidgets
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
    def sync_system_settings(self):
        if self._sync_system_settings is None:
            self._sync_system_settings = get_system_settings()["modules"].\
                get("sync_server")

        return self._sync_system_settings

    @property
    def sync_project_settings(self):
        if self._sync_project_settings is None:
            self.set_sync_project_settings()

        return self._sync_project_settings

    def set_sync_project_settings(self, exclude_locals=False):
        """
            Set sync_project_settings for all projects (caching)
            Args:
                exclude_locals (bool): ignore overrides from Local Settings
            For performance
        """
        sync_project_settings = self._prepare_sync_project_settings(
            exclude_locals)

        self._sync_project_settings = sync_project_settings

    def _prepare_sync_project_settings(self, exclude_locals):
        sync_project_settings = {}
        system_sites = self.get_all_site_configs()
        project_docs = get_projects(fields=["name"])
        for project_doc in project_docs:
            project_name = project_doc["name"]
            sites = copy.deepcopy(system_sites)  # get all configured sites
            proj_settings = self._parse_sync_settings_from_settings(
                get_project_settings(project_name,
                                     exclude_locals=exclude_locals))
            sites.update(self._get_default_site_configs(
                proj_settings["enabled"], project_name))
            sites.update(proj_settings['sites'])
            proj_settings["sites"] = sites

            sync_project_settings[project_name] = proj_settings
        if not sync_project_settings:
            self.log.info("No enabled and configured projects for sync.")
        return sync_project_settings

    def get_sync_project_setting(self, project_name, exclude_locals=False,
                                 cached=True):
        """ Handles pulling sync_server's settings for enabled 'project_name'

            Args:
                project_name (str): used in project settings
                exclude_locals (bool): ignore overrides from Local Settings
                cached (bool): use pre-cached values, or return fresh ones
                    cached values needed for single loop (with all overrides)
                    fresh values needed for Local settings (without overrides)
            Returns:
                (dict): settings dictionary for the enabled project,
                    empty if no settings or sync is disabled
        """
        # presets set already, do not call again and again
        # self.log.debug("project preset {}".format(self.presets))
        if not cached:
            return self._prepare_sync_project_settings(exclude_locals)\
                [project_name]

        if not self.sync_project_settings or \
               not self.sync_project_settings.get(project_name):
            self.set_sync_project_settings(exclude_locals)

        return self.sync_project_settings.get(project_name)

    def _parse_sync_settings_from_settings(self, settings):
        """ settings from api.get_project_settings, TOOD rename """
        sync_settings = settings.get("global").get("sync_server")

        return sync_settings

    def get_all_site_configs(self, project_name=None,
                             local_editable_only=False):
        """
            Returns (dict) with all sites configured system wide.

            Args:
                project_name (str)(optional): if present, check if not disabled
                local_editable_only (bool)(opt): if True return only Local
                    Setting configurable (for LS UI)
            Returns:
                (dict): {'studio': {'provider':'local_drive'...},
                         'MY_LOCAL': {'provider':....}}
        """
        sync_sett = self.sync_system_settings
        project_enabled = True
        project_settings = None
        if project_name:
            project_enabled = project_name in self.get_enabled_projects()
            project_settings = self.get_sync_project_setting(project_name)
        sync_enabled = sync_sett["enabled"] and project_enabled

        system_sites = {}
        if sync_enabled:
            for site, detail in sync_sett.get("sites", {}).items():
                if project_settings:
                    site_settings = project_settings["sites"].get(site)
                    if site_settings:
                        detail.update(site_settings)
                system_sites[site] = detail
        system_sites.update(self._get_default_site_configs(sync_enabled,
                                                           project_name))
        if local_editable_only:
            local_schema = SyncServerModule.get_local_settings_schema()
            editable_keys = {}
            for provider_code, editables in local_schema.items():
                editable_keys[provider_code] = ["enabled", "provider"]
                for editable_item in editables:
                    editable_keys[provider_code].append(editable_item["key"])

            for _, site in system_sites.items():
                provider = site["provider"]
                for site_config_key in list(site.keys()):
                    if site_config_key not in editable_keys[provider]:
                        site.pop(site_config_key, None)

        return system_sites

    def _get_default_site_configs(self, sync_enabled=True, project_name=None):
        """
            Returns settings for 'studio' and user's local site

            Returns base values from setting, not overridden by Local Settings,
            eg. value used to push TO LS not to get actual value for syncing.
        """
        if not project_name:
            anatomy_sett = get_default_anatomy_settings(exclude_locals=True)
        else:
            anatomy_sett = get_anatomy_settings(project_name,
                                                exclude_locals=True)
        roots = {}
        for root, config in anatomy_sett["roots"].items():
            roots[root] = config
        studio_config = {
            'enabled': True,
            'provider': 'local_drive',
            "root": roots
        }
        all_sites = {self.DEFAULT_SITE: studio_config}
        if sync_enabled:
            all_sites[get_local_site_id()] = {'enabled': True,
                                              'provider': 'local_drive',
                                              "root": roots}
            # duplicate values for normalized local name
            all_sites["local"] = {
                'enabled': True,
                'provider': 'local_drive',
                "root": roots}
        return all_sites

    def get_provider_for_site(self, project_name=None, site=None):
        """
            Return provider name for site (unique name across all projects.
        """
        sites = {self.DEFAULT_SITE: "local_drive",
                 self.LOCAL_SITE: "local_drive",
                 get_local_site_id(): "local_drive"}

        if site in sites.keys():
            return sites[site]

        if project_name:  # backward compatibility
            proj_settings = self.get_sync_project_setting(project_name)
            provider = proj_settings.get("sites", {}).get(site, {}).\
                get("provider")
            if provider:
                return provider

        sync_sett = self.sync_system_settings
        for conf_site, detail in sync_sett.get("sites", {}).items():
            sites[conf_site] = detail.get("provider")

        return sites.get(site, 'N/A')

    @time_function
    def get_sync_representations(self, project_name, active_site, remote_site):
        """
            Get representations that should be synced, these could be
            recognised by presence of document in 'files.sites', where key is
            a provider (GDrive, S3) and value is empty document or document
            without 'created_dt' field. (Don't put null to 'created_dt'!).

            Querying of 'to-be-synched' files is offloaded to Mongod for
            better performance. Goal is to get as few representations as
            possible.
        Args:
            project_name (string):
            active_site (string): identifier of current active site (could be
                'local_0' when working from home, 'studio' when working in the
                studio (default)
            remote_site (string): identifier of remote site I want to sync to

        Returns:
            (list) of dictionaries
        """
        self.log.debug("Check representations for : {}".format(project_name))
        self.connection.Session["AVALON_PROJECT"] = project_name
        # retry_cnt - number of attempts to sync specific file before giving up
        retries_arr = self._get_retries_arr(project_name)
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
                                "tries": {"$in": retries_arr},
                                "paused": {"$exists": False}
                            }
                        }
                    }]},
                {"$and": [
                    {
                        "files.sites": {
                            "$elemMatch": {
                                "name": active_site,
                                "created_dt": {"$exists": False},
                                "tries": {"$in": retries_arr},
                                "paused": {"$exists": False}
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
        self.log.debug("active_site:{} - remote_site:{}".format(
            active_site, remote_site
        ))
        self.log.debug("query: {}".format(aggr))
        representations = self.connection.aggregate(aggr)

        return representations

    def check_status(self, file, local_site, remote_site, config_preset):
        """
            Check synchronization status for single 'file' of single
            'representation' by single 'provider'.
            (Eg. check if 'scene.ma' of lookdev.v10 should be synced to GDrive

            Always is comparing local record, eg. site with
            'name' == self.presets[PROJECT_NAME]['config']["active_site"]

            This leads to trigger actual upload or download, there is
            a use case 'studio' <> 'remote' where user should publish
            to 'studio', see progress in Tray GUI, but do not do
            physical upload/download
            (as multiple user would be doing that).

            Do physical U/D only when any of the sites is user's local, in that
            case only user has the data and must U/D.

        Args:
            file (dictionary):  of file from representation in Mongo
            local_site (string):  - local side of compare (usually 'studio')
            remote_site (string):  - gdrive etc.
            config_preset (dict): config about active site, retries
        Returns:
            (string) - one of SyncStatus
        """
        sites = file.get("sites") or []

        if get_local_site_id() not in (local_site, remote_site):
            # don't do upload/download for studio sites
            self.log.debug(
                "No local site {} - {}".format(local_site, remote_site)
            )
            return SyncStatus.DO_NOTHING

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

    def update_db(self, project_name, new_file_id, file, representation,
                  site, error=None, progress=None, priority=None):
        """
            Update 'provider' portion of records in DB with success (file_id)
            or error (exception)

        Args:
            project_name (string): name of project - force to db connection as
              each file might come from different collection
            new_file_id (string): only present if file synced successfully
            file (dictionary): info about processed file (pulled from DB)
            representation (dictionary): parent repr of file (from DB)
            site (string): label ('gdrive', 'S3')
            error (string): exception message
            progress (float): 0-0.99 of progress of upload/download
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

        self.connection.database[project_name].update_one(
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
        self.log.debug(
            (
                "File for {} - {source_file} process {status} {error_str}"
            ).format(
                representation_id,
                status=status,
                source_file=source_file,
                error_str=error_str
            )
        )

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

    def reset_site_on_representation(self, project_name, representation_id,
                                     side=None, file_id=None, site_name=None,
                                     remove=False, pause=None, force=False,
                                     priority=None):
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
            project_name (string): name of project (eg. collection) in DB
            representation_id(string): _id of representation
            file_id (string):  file _id in representation
            side (string): local or remote side
            site_name (string): for adding new site
            remove (bool): if True remove site altogether
            pause (bool or None): if True - pause, False - unpause
            force (bool): hard reset - currently only for add_site
            priority (int): set priority

        Raises:
            SiteAlreadyPresentError - if adding already existing site and
                not 'force'
            ValueError - other errors (repre not found, misconfiguration)
        """
        representation = get_representation_by_id(project_name,
                                                  representation_id)
        if not representation:
            raise ValueError("Representation {} not found in {}".
                             format(representation_id, project_name))

        if side and site_name:
            raise ValueError("Misconfiguration, only one of side and " +
                             "site_name arguments should be passed.")

        local_site = self.get_active_site(project_name)
        remote_site = self.get_remote_site(project_name)

        if side:
            if side == 'local':
                site_name = local_site
            else:
                site_name = remote_site

        elem = {"name": site_name}

        # Add priority
        if priority:
            elem["priority"] = priority

        if file_id:  # reset site for particular file
            self._reset_site_for_file(project_name, representation_id,
                                      elem, file_id, site_name)
        elif side:  # reset site for whole representation
            self._reset_site(project_name, representation_id, elem, site_name)
        elif remove:  # remove site for whole representation
            self._remove_site(project_name,
                              representation, site_name)
        elif pause is not None:
            self._pause_unpause_site(project_name,
                                     representation, site_name, pause)
        else:  # add new site to all files for representation
            self._add_site(project_name, representation, elem, site_name,
                           force=force)

    def _update_site(self, project_name, representation_id,
                     update, arr_filter):
        """
            Auxiliary method to call update_one function on DB

            Used for refactoring ugly reset_provider_for_file
        """
        query = {
            "_id": ObjectId(representation_id)
        }

        self.connection.database[project_name].update_one(
            query,
            update,
            upsert=True,
            array_filters=arr_filter
        )

    def _reset_site_for_file(self, project_name, representation_id,
                             elem, file_id, site_name):
        """
            Resets 'site_name' for 'file_id' on representation in 'query' on
            'project_name'
        """
        update = {
            "$set": {"files.$[f].sites.$[s]": elem}
        }
        if not isinstance(file_id, ObjectId):
            file_id = ObjectId(file_id)

        arr_filter = [
            {'s.name': site_name},
            {'f._id': file_id}
        ]

        self._update_site(project_name, representation_id, update, arr_filter)

    def _reset_site(self, project_name, representation_id, elem, site_name):
        """
            Resets 'site_name' for all files of representation in 'query'
        """
        update = {
            "$set": {"files.$[].sites.$[s]": elem}
        }

        arr_filter = [
            {'s.name': site_name}
        ]

        self._update_site(project_name, representation_id, update, arr_filter)

    def _remove_site(self, project_name, representation, site_name):
        """
            Removes 'site_name' for 'representation' in 'query'

            Throws ValueError if 'site_name' not found on 'representation'
        """
        found = False
        for repre_file in representation.get("files"):
            for site in repre_file.get("sites"):
                if site.get("name") == site_name:
                    found = True
                    break
        if not found:
            msg = "Site {} not found".format(site_name)
            self.log.info(msg)
            raise ValueError(msg)

        update = {
            "$pull": {"files.$[].sites": {"name": site_name}}
        }
        arr_filter = []

        self._update_site(project_name, representation["_id"],
                          update, arr_filter)

    def _pause_unpause_site(self, project_name, representation,
                            site_name, pause):
        """
            Pauses/unpauses all files for 'representation' based on 'pause'

            Throws ValueError if 'site_name' not found on 'representation'
        """
        found = False
        site = None
        for repre_file in representation.get("files"):
            for site in repre_file.get("sites"):
                if site["name"] == site_name:
                    found = True
                    break
        if not found:
            msg = "Site {} not found".format(site_name)
            self.log.info(msg)
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

        self._update_site(project_name, representation["_id"],
                          update, arr_filter)

    def _add_site(self, project_name, representation, elem, site_name,
                  force=False, file_id=None):
        """
            Adds 'site_name' to 'representation' on 'project_name'

            Args:
                representation (dict)
                file_id (ObjectId)

            Use 'force' to remove existing or raises ValueError
        """
        representation_id = representation["_id"]
        reset_existing = False
        files = representation.get("files", [])
        if not files:
            self.log.debug("No files for {}".format(representation_id))
            return

        for repre_file in files:
            if file_id and file_id != repre_file["_id"]:
                continue

            for site in repre_file.get("sites"):
                if site["name"] == site_name:
                    if force or site.get("error"):
                        self._reset_site_for_file(project_name,
                                                  representation_id,
                                                  elem, repre_file["_id"],
                                                  site_name)
                        reset_existing = True
                    else:
                        msg = "Site {} already present".format(site_name)
                        self.log.info(msg)
                        raise SiteAlreadyPresentError(msg)

        if reset_existing:
            return

        if not file_id:
            update = {
                "$push": {"files.$[].sites": elem}
            }

            arr_filter = []
        else:
            update = {
                "$push": {"files.$[f].sites": elem}
            }
            arr_filter = [
                {'f._id': file_id}
            ]

        self._update_site(project_name, representation_id,
                          update, arr_filter)

    def _remove_local_file(self, project_name, representation_id, site_name):
        """
            Removes all local files for 'site_name' of 'representation_id'

            Args:
                project_name (string): project name (must match DB)
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

        provider_name = self.get_provider_for_site(site=site_name)

        if provider_name == 'local_drive':
            representation = get_representation_by_id(project_name,
                                                      representation_id,
                                                      fields=["files"])
            if not representation:
                self.log.debug("No repre {} found".format(
                    representation_id))
                return

            local_file_path = ''
            for file in representation.get("files"):
                local_file_path = self.get_local_file_path(project_name,
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
        if not project_name:
            return 60

        ld = self.sync_project_settings[project_name]["config"]["loop_delay"]
        return int(ld)

    def show_widget(self):
        """Show dialog for Sync Queue"""
        no_errors = False
        try:
            from .tray.app import SyncServerWindow
            self.widget = SyncServerWindow(self)
            no_errors = True
        except ValueError:
            self.log.info(
                "No system setting for sync. Not syncing.", exc_info=True
            )
        except KeyError:
            self.log.info((
                "There are not set presets for SyncServer OR "
                "Credentials provided are invalid, "
                "no syncing possible").
                format(str(self.sync_project_settings)), exc_info=True)
        except:
            self.log.error(
                "Uncaught exception durin start of SyncServer",
                exc_info=True)
        self.enabled = no_errors
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
        return self._get_tries_count_from_rec(rec)

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

    def cli(self, click_group):
        click_group.add_command(cli_main.to_click_obj())

    # Webserver module implementation
    def webserver_initialization(self, server_manager):
        """Add routes for syncs."""
        if self.tray_initialized:
            from .rest_api import SyncServerModuleRestApi
            self.rest_api_obj = SyncServerModuleRestApi(
                self, server_manager
            )


@click_wrap.group(
    SyncServerModule.name,
    help="SyncServer module related commands.")
def cli_main():
    pass


@cli_main.command()
@click_wrap.option(
    "-a",
    "--active_site",
    required=True,
    help="Name of active stie")
def syncservice(active_site):
    """Launch sync server under entered site.

    This should be ideally used by system service (such us systemd or upstart
    on linux and window service).
    """

    from openpype.modules import ModulesManager

    os.environ["OPENPYPE_LOCAL_ID"] = active_site

    def signal_handler(sig, frame):
        print("You pressed Ctrl+C. Process ended.")
        sync_server_module.server_exit()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    manager = ModulesManager()
    sync_server_module = manager.modules_by_name["sync_server"]

    sync_server_module.server_init()
    sync_server_module.server_start()

    while True:
        time.sleep(1.0)
