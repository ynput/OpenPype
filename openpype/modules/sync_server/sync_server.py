"""Python 3 only implementation."""
import os
import re
import shutil
import asyncio
import threading
import concurrent.futures
from time import sleep
from concurrent.futures._base import CancelledError

from .providers import lib
from openpype.client.entity_links import get_linked_representation_id
from openpype.lib import Logger
from openpype.lib.local_settings import get_local_site_id
from openpype.modules.base import ModulesManager
from openpype.pipeline import Anatomy
from openpype.pipeline.template_data import get_template_data_with_names
from openpype.pipeline.load.utils import get_representation_path_with_anatomy
from openpype.pipeline.workfile.path_resolving import (
    get_workfile_template_key,
    get_workdir,
)
from openpype.settings.lib import get_project_settings
from openpype.client.entities import get_asset_by_name, get_project

from .utils import SyncStatus, ResumableError


async def upload(module, project_name, file, representation, provider_name,
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
        module(SyncServerModule): object to run SyncServerModule API
        project_name (str): source db
        file (dictionary): of file from representation in Mongo
        representation (dictionary): of representation
        provider_name (string): gdrive, gdc etc.
        site_name (string): site on provider, single provider(gdrive) could
            have multiple sites (different accounts, credentials)
        tree (dictionary): injected memory structure for performance
        preset (dictionary): site config ('credentials_url', 'root'...)

    """
    # create ids sequentially, upload file in parallel later
    with module.lock:
        # this part modifies structure on 'remote_site', only single
        # thread can do that at a time, upload/download to prepared
        # structure should be run in parallel
        remote_handler = lib.factory.get_provider(provider_name,
                                                  project_name,
                                                  remote_site_name,
                                                  tree=tree,
                                                  presets=preset)

        file_path = file.get("path", "")
        try:
            local_file_path, remote_file_path = resolve_paths(
                module, file_path, project_name,
                remote_site_name, remote_handler
            )
        except Exception as exp:
            print(exp)

        target_folder = os.path.dirname(remote_file_path)
        folder_id = remote_handler.create_folder(target_folder)

        if not folder_id:
            err = "Folder {} wasn't created. Check permissions.". \
                format(target_folder)
            raise NotADirectoryError(err)

    loop = asyncio.get_running_loop()
    file_id = await loop.run_in_executor(None,
                                         remote_handler.upload_file,
                                         local_file_path,
                                         remote_file_path,
                                         module,
                                         project_name,
                                         file,
                                         representation,
                                         remote_site_name,
                                         True
                                         )

    module.handle_alternate_site(project_name, representation,
                                 remote_site_name,
                                 file["_id"], file_id)

    return file_id


async def download(module, project_name, file, representation, provider_name,
                   remote_site_name, tree=None, preset=None):
    """
        Downloads file to local folder denoted in representation.Context.

    Args:
        module(SyncServerModule): object to run SyncServerModule API
        project_name (str): source
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
    with module.lock:
        remote_handler = lib.factory.get_provider(provider_name,
                                                  project_name,
                                                  remote_site_name,
                                                  tree=tree,
                                                  presets=preset)

        file_path = file.get("path", "")
        local_file_path, remote_file_path = resolve_paths(
            module, file_path, project_name, remote_site_name, remote_handler
        )

        local_folder = os.path.dirname(local_file_path)
        os.makedirs(local_folder, exist_ok=True)

    local_site = module.get_active_site(project_name)

    loop = asyncio.get_running_loop()
    file_id = await loop.run_in_executor(None,
                                         remote_handler.download_file,
                                         remote_file_path,
                                         local_file_path,
                                         module,
                                         project_name,
                                         file,
                                         representation,
                                         local_site,
                                         True
                                         )

    module.handle_alternate_site(project_name, representation, local_site,
                                 file["_id"], file_id)

    return file_id


def resolve_paths(module, file_path, project_name,
                  remote_site_name=None, remote_handler=None):
    """
        Returns tuple of local and remote file paths with {root}
        placeholders replaced with proper values from Settings or Anatomy

        Ejected here because of Python 2 hosts (GDriveHandler is an issue)

        Args:
            module(SyncServerModule): object to run SyncServerModule API
            file_path(string): path with {root}
            project_name(string): project name
            remote_site_name(string): remote site
            remote_handler(AbstractProvider): implementation
        Returns:
            (string, string) - proper absolute paths, remote path is optional
    """
    remote_file_path = ''
    if remote_handler:
        remote_file_path = remote_handler.resolve_path(file_path)

    local_handler = lib.factory.get_provider(
        'local_drive', project_name, module.get_active_site(project_name))
    local_file_path = local_handler.resolve_path(file_path)

    return local_file_path, remote_file_path


def site_is_working(module, project_name, site_name):
    """
        Confirm that 'site_name' is configured correctly for 'project_name'.

        Must be here as lib.factory access doesn't work in Python 2 hosts.

        Args:
            module (SyncServerModule)
            project_name(string):
            site_name(string):
        Returns
            (bool)
    """
    if _get_configured_sites(module, project_name).get(site_name):
        return True
    return False


def _get_configured_sites(module, project_name):
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
    settings = module.get_sync_project_setting(project_name)
    return _get_configured_sites_from_setting(module, project_name, settings)


def _get_configured_sites_from_setting(module, project_name, project_setting):
    if not project_setting.get("enabled"):
        return {}

    initiated_handlers = {}
    configured_sites = {}
    all_sites = module._get_default_site_configs()
    all_sites.update(project_setting.get("sites"))
    for site_name, config in all_sites.items():
        provider = module.get_provider_for_site(site=site_name)
        handler = initiated_handlers.get((provider, site_name))
        if not handler:
            handler = lib.factory.get_provider(provider,
                                               project_name,
                                               site_name,
                                               presets=config)
            initiated_handlers[(provider, site_name)] = \
                handler

        if handler.is_active():
            configured_sites[site_name] = True

    return configured_sites


def get_last_published_workfile_path(
    host_name: str,
    project_name: str,
    task_name: str,
    workfile_representation: dict,
    anatomy: Anatomy = None,
) -> str:
    """Get last published workfile path.

    Args:
        host_name (str): Host name.
        project_name (str): Project name.
        task_name (str): Task name.
        workfile_representation (dict): Workfile representation.
        anatomy (Anatomy, optional): Anatomy (Used for optimization).
            Defaults to None.

    Returns:
        str: Last published workfile path.
    """
    if not anatomy:
        anatomy = Anatomy(project_name)

    if not workfile_representation:
        print(
            "No published workfile for task '{}' and host '{}'.".format(
                task_name, host_name
            )
        )
        return

    return get_representation_path_with_anatomy(
        workfile_representation, anatomy
    )


def download_last_published_workfile(
    host_name: str,
    project_name: str,
    asset_name: str,
    task_name: str,
    last_published_workfile_path: str,
    workfile_representation: dict,
    subset_id: str,
    last_version_doc: dict,
    anatomy: Anatomy = None,
    asset_doc: dict = None,
) -> str:
    """Download the last published workfile, and return its path.

    Args:
        host_name (str): Host name.
        project_name (str): Project name.
        asset_name (str): Asset name.
        task_name (str): Task name.
        last_published_workfile_path (str): Last published workfile
            path.
        workfile_representation (dict): Workfile representation.
        subset_id (str): Subset ID.
        last_version_doc (dict): Last version doc.
        anatomy (Anatomy, optional): Anatomy (Used for optimization).
            Defaults to None.
        asset_doc (dict, optional): Asset doc (Used for optimization).
            Defaults to None.

    Returns:
        str: New local workfile path.
    """

    if not anatomy:
        anatomy = Anatomy(project_name)

    if not asset_doc:
        asset_doc = get_asset_by_name(project_name, asset_name)

    # Get sync server module
    sync_server = ModulesManager().modules_by_name.get("sync_server")
    if not sync_server or not sync_server.enabled:
        print("Sync server module is disabled or unavailable.")
        return

    if subset_id is None:
        print(
            "Not any matched subset for task '{}' of '{}'.".format(
                task_name, asset_name
            )
        )
        return

    if not workfile_representation:
        print(
            "Not published workfile for task '{}' and host '{}'.".format(
                task_name, host_name
            )
        )
        return

    # If representation isn't available on remote site, then return.
    if not sync_server.is_representation_on_site(
        project_name,
        workfile_representation["_id"],
        sync_server.get_remote_site(project_name),
    ):
        print(
            "Representation for task '{}' and host '{}'".format(
                task_name, host_name
            )
        )
        return

    # Get local site
    local_site_id = get_local_site_id()

    # Add workfile representation to local site
    representation_ids = {workfile_representation["_id"]}
    representation_ids.update(
        get_linked_representation_id(
            project_name, repre_id=workfile_representation["_id"]
        )
    )
    for repre_id in representation_ids:
        sync_server.add_site(
            project_name,
            repre_id,
            local_site_id,
            force=True,
            priority=99,
            reset_timer=True,
        )

    # While representation unavailable locally, wait.
    while not sync_server.is_representation_on_site(
        project_name, workfile_representation["_id"], local_site_id
    ):
        sleep(5)

    if not last_published_workfile_path:
        last_published_workfile_path = get_last_published_workfile_path(
            host_name,
            project_name,
            task_name,
            workfile_representation,
            anatomy=anatomy,
        )

    # Get workfile data
    workfile_data = get_template_data_with_names(
        project_name, asset_name, task_name, host_name
    )

    extension = last_published_workfile_path.split(".")[-1]

    project_settings = get_project_settings(project_name)
    template_key = get_workfile_template_key(
        task_name, host_name, project_name, project_settings
    )

    # Get version patter for regex search
    version_pattern = anatomy.templates[template_key]["version"]
    version_pattern = re.sub(
        r"{version.*?}",
        r"([0-9]+)",
        version_pattern,
    )

    # Get local workfile version number
    last_local_workfile_version = None
    for filename in sorted(
        os.listdir(
            get_workdir(
                get_project(project_name),
                asset_doc,
                task_name,
                host_name,
                anatomy=anatomy,
                template_key=template_key,
                project_settings=project_settings,
            )
        ),
        reverse=True,
    ):
        if filename.endswith(extension):
            match = re.search(
                version_pattern,
                filename
            )
            if match:
                last_local_workfile_version = int(match.group(1))
                break
    
    # Set workfile data workfile version
    # Either last published version or last local version, whichever is higher
    workfile_data["version"] = (
        last_local_workfile_version + 1
        if (
            last_local_workfile_version
            and last_local_workfile_version > last_version_doc["name"]
        )
        else last_version_doc["name"] + 1
    )
    workfile_data["ext"] = extension

    anatomy_result = anatomy.format(workfile_data)
    local_workfile_path = anatomy_result[template_key]["path"]

    # Copy last published workfile to local workfile directory
    shutil.copy(
        last_published_workfile_path,
        local_workfile_path,
    )

    return local_workfile_path


class SyncServerThread(threading.Thread):
    """
        Separate thread running synchronization server with asyncio loop.
        Stopped when tray is closed.
    """
    def __init__(self, module):
        self.log = Logger.get_logger(self.__class__.__name__)

        super(SyncServerThread, self).__init__()
        self.module = module
        self.loop = None
        self.is_running = False
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self.timer = None

    def run(self):
        self.is_running = True

        try:
            self.log.info("Starting Sync Server")
            self.loop = asyncio.new_event_loop()  # create new loop for thread
            asyncio.set_event_loop(self.loop)
            self.loop.set_default_executor(self.executor)

            asyncio.ensure_future(self.check_shutdown(), loop=self.loop)
            asyncio.ensure_future(self.sync_loop(), loop=self.loop)
            self.log.info("Sync Server Started")
            self.loop.run_forever()
        except Exception:
            self.log.warning(
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
                - for each project_name it looks for representations that
                  should be synced
                - synchronize found collections
                - update representations - fills error messages for exceptions
                - waits X seconds and repeat
        Returns:

        """
        while self.is_running and not self.module.is_paused():
            try:
                import time
                start_time = time.time()
                self.module.set_sync_project_settings()  # clean cache
                project_name = None
                enabled_projects = self.module.get_enabled_projects()
                for project_name in enabled_projects:
                    preset = self.module.sync_project_settings[project_name]

                    local_site, remote_site = self._working_sites(project_name)
                    if not all([local_site, remote_site]):
                        continue

                    sync_repres = self.module.get_sync_representations(
                        project_name,
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
                    remote_provider = \
                        self.module.get_provider_for_site(site=remote_site)
                    handler = lib.factory.get_provider(remote_provider,
                                                       project_name,
                                                       remote_site,
                                                       presets=site_preset)
                    limit = lib.factory.get_provider_batch_limit(
                        remote_provider)
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
                                        upload(self.module,
                                               project_name,
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
                                                                 project_name
                                                                 ))
                                    processed_file_path.add(file_path)
                                if status == SyncStatus.DO_DOWNLOAD:
                                    tree = handler.get_tree()
                                    limit -= 1
                                    task = asyncio.create_task(
                                        download(self.module,
                                                 project_name,
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
                                                                 project_name
                                                                 ))
                                    processed_file_path.add(file_path)

                    self.log.debug("Sync tasks count {}".format(
                        len(task_files_to_process)
                    ))
                    files_created = await asyncio.gather(
                        *task_files_to_process,
                        return_exceptions=True)
                    for file_id, info in zip(files_created,
                                             files_processed_info):
                        file, representation, site, project_name = info
                        error = None
                        if isinstance(file_id, BaseException):
                            error = str(file_id)
                            file_id = None
                        self.module.update_db(project_name,
                                              file_id,
                                              file,
                                              representation,
                                              site,
                                              error)

                duration = time.time() - start_time
                self.log.debug("One loop took {:.2f}s".format(duration))

                delay = self.module.get_loop_delay(project_name)
                self.log.debug(
                    "Waiting for {} seconds to new loop".format(delay)
                )
                self.timer = asyncio.create_task(self.run_timer(delay))
                await asyncio.gather(self.timer)

            except ConnectionResetError:
                self.log.warning(
                    "ConnectionResetError in sync loop, trying next loop",
                    exc_info=True)
            except CancelledError:
                # just stopping server
                pass
            except ResumableError:
                self.log.warning(
                    "ResumableError in sync loop, trying next loop",
                    exc_info=True)
            except Exception:
                self.stop()
                self.log.warning(
                    "Unhandled except. in sync loop, stopping server",
                    exc_info=True)

    def stop(self):
        """Sets is_running flag to false, 'check_shutdown' shuts server down"""
        self.is_running = False

    async def check_shutdown(self):
        """ Future that is running and checks if server should be running
            periodically.
        """
        while self.is_running:
            if self.module.long_running_tasks:
                task = self.module.long_running_tasks.pop()
                self.log.info("starting long running")
                await self.loop.run_in_executor(None, task["func"])
                self.log.info("finished long running")
                self.module.projects_processed.remove(task["project_name"])
            await asyncio.sleep(0.5)
        tasks = [task for task in asyncio.all_tasks() if
                 task is not asyncio.current_task()]
        list(map(lambda task: task.cancel(), tasks))  # cancel all the tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        self.log.debug(
            f'Finished awaiting cancelled tasks, results: {results}...')
        await self.loop.shutdown_asyncgens()
        # to really make sure everything else has time to stop
        self.executor.shutdown(wait=True)
        await asyncio.sleep(0.07)
        self.loop.stop()

    async def run_timer(self, delay):
        """Wait for 'delay' seconds to start next loop"""
        await asyncio.sleep(delay)

    def reset_timer(self):
        """Called when waiting for next loop should be skipped"""
        self.log.debug("Resetting timer")
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def _working_sites(self, project_name):
        if self.module.is_project_paused(project_name):
            self.log.debug("Both sites same, skipping")
            return None, None

        local_site = self.module.get_active_site(project_name)
        remote_site = self.module.get_remote_site(project_name)
        if local_site == remote_site:
            self.log.debug("{}-{} sites same, skipping".format(
                local_site, remote_site))
            return None, None

        configured_sites = _get_configured_sites(self.module, project_name)
        if not all([local_site in configured_sites,
                    remote_site in configured_sites]):
            self.log.debug(
                "Some of the sites {} - {} is not working properly".format(
                    local_site, remote_site
                )
            )

            return None, None

        return local_site, remote_site
