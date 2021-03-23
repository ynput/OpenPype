"""Python 3 only implementation."""
import os
import asyncio
import threading
import concurrent.futures
from concurrent.futures._base import CancelledError

from .providers import lib
from pype.lib import PypeLogger

from .utils import SyncStatus


log = PypeLogger().get_logger("SyncServer")


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
            err = "Folder {} wasn't created. Check permissions.". \
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
                for collection, preset in self.module.sync_project_settings.\
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
