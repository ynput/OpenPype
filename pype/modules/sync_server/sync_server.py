from pype.api import config, Logger
from avalon import io

import threading
import asyncio
import concurrent.futures

from enum import Enum
from datetime import datetime

from .providers import lib
import os

log = Logger().get_logger("SyncServer")

# test object 5eeb25e411e06a16209ab78e


class SyncStatus(Enum):
    DO_NOTHING = 0
    DO_UPLOAD = 1
    DO_DOWNLOAD = 2


class SyncServer():
    """
        WIP
       Synchronization server that is synching published files from local to
       any of implemented providers (like GDrive, S3 etc.)
       Runs in the background and checks all representations, looks for files
       that are marked to be in different location than 'studio' (temporary),
       checks if 'created_dt' field is present denoting successfull synch
       with provider destination.

       ''' - example of synced file test_Cylinder_lookMain_v010.ma to GDrive
        "files" : [
        {
            "path" : "{root}/Test/Assets/Cylinder/publish/look/lookMain/v010/
                     test_Cylinder_lookMain_v010.ma",
            "_id" : ObjectId("5eeb25e411e06a16209ab78f"),
            "hash" : "test_Cylinder_lookMain_v010,ma|1592468963,24|4822",
            "size" : NumberLong(4822),
            "sites" : {
                "studio" : {
                    "created_dt" : ISODate("2020-05-22T08:05:44.000Z")
                },
                "gdrive" : {
                    "id" : ObjectId("5eeb25e411e06a16209ab78f"),
                    "created_dt" : ISODate("2020-07-16T17:54:35.833Z")
                }
            }
        },
        '''
        It is expected that multiple providers will be implemented in separate
        classes and registered in 'providers.py'.

    """
    RETRY_CNT = 3  # number of attempts to sync specific file

    def __init__(self):
        self.qaction = None
        self.failed_icon = None
        self._is_running = False
        self.presets = None
        self.lock = threading.Lock()

        if not io.Session:
            io.install()

        io.Session['AVALON_PROJECT'] = 'Test'
        try:
            self.presets = config.get_presets()["services"]["sync_server"]
        except Exception:

            log.debug((
                          "There are not set presets for SyncServer."
                          " No credentials provided, no synching possible"
                      ).format(str(self.presets)))
        handler = lib.factory.get_provider('gdrive')  # prime handler TEMP
        self.sync_server_thread = SynchServerThread(self)

    def get_sync_representations(self):
        """
            Get representations that should be synched, these could be
            recognised by presence of document in 'files.sites', where key is
            a provider (GDrive, S3) and value is empty document or document with
            no value for 'created_dt' field.
            Currently returning all representations.
                TODO: filter out representations that shouldnt be synced
        :return: <list>
        """
        representations = io.find({
            "type": "representation"
        })

        return representations

    def check_status(self, file, representation, provider):
        """
            Check synchronization status for single 'file' of single
            'representation' by single 'provider'.
            (Eg. check if 'scene.ma' of lookdev.v10 should be synched to GDrive
        :param file: <dictionary> of file from representation in Mongo
        :param representation: <dictionary> of representation
        :param provider: <string> - gdrive, gdc etc.
        :return: <string> - one of SyncStatus
        """
        sites = file.get("sites") or {}
        if isinstance(sites, list):  # temporary, old format of 'sites'
            return SyncStatus.DO_NOTHING
        provider_rec = sites.get(provider) or {}
        if provider_rec:
            created_dt = provider_rec.get("created_dt")
            if not created_dt:
                tries = self._get_tries_count(file, provider)
                # file will be skipped if unsuccessfully tried over threshold
                # error metadata needs to be purged manually in DB to reset
                if tries < self.RETRY_CNT:
                    return SyncStatus.DO_UPLOAD

        return SyncStatus.DO_NOTHING

    async def upload(self, file, representation, provider, tree=None):
        """
            Upload single 'file' of a 'representation' to 'provider'.
            Source url is taken from 'file' portion, where {root} placeholder
            is replaced by 'representation.Context.root'
            Provider could be one of implemented in provider.py.

            Updates MongoDB, fills in id of file from provider (ie. file_id
            from GDrive), 'created_dt' - time of upload

        :param file: <dictionary> of file from representation in Mongo
        :param representation: <dictionary> of representation
        :param provider: <string> - gdrive, gdc etc.
        :return:
        """
        # create ids sequentially, upload file in parallel later
        with self.lock:
            handler = lib.factory.get_provider(provider, tree)
            local_root = representation.get("context", {}).get("root")
            if not local_root:
                raise ValueError("Unknown local root for file {}")
            source_file = file.get("path", "").replace('{root}', local_root)
            target_root = '/{}'.format(handler.get_root_name())
            target_file = file.get("path", "").replace('{root}', target_root)

            target_folder = os.path.dirname(target_file)
            folder_id = handler.create_folder(target_folder)

            if not folder_id:
                raise NotADirectoryError("Folder {} wasn't created"
                                         .format(target_folder))

        loop = asyncio.get_running_loop()
        file_id = await loop.run_in_executor(None,
                                             handler.upload_file,
                                             source_file,
                                             target_file,
                                             True)
        return file_id

    def update_db(self, new_file_id, file, representation,provider,error=None):
        """
            Update 'provider' portion of records in DB with success (file_id)
            or error (exception)
        :param new_file_id: <string>
        :param file: <dictionary> - info about processed file (pulled from DB)
        :param representation: <dictionary> - parent repr of file (from DB)
        :param provider: <string> - label ('gdrive', 'S3')
        :param error: <string> - exception message
        :return: None
        """
        representation_id = representation.get("_id")
        file_id = file.get("_id")
        query = {
            "_id": representation_id,
            "files._id": file_id
        }

        update = {}
        if new_file_id:
            update["$set"] = self._get_success_dict(provider, new_file_id)
            # reset previous errors if any
            update["$unset"] = self._get_error_dict(provider, "", "")
        else:
            tries = self._get_tries_count(file, provider)
            tries += 1

            update["$set"] = self._get_error_dict(provider, error, tries)

        # it actually modifies single _id, but io.update_one not implemented
        io.update_many(
            query,
            update
        )
        status = 'failed'
        if new_file_id:
            status = 'succeeded with id {}'.format(new_file_id)
        source_file = file.get("path", "")
        log.debug("File {} upload {} {}".format(status, source_file, status))

    async def download(self, file, representation, provider):
        pass

    def tray_start(self):
        self.sync_server_thread.start()

    def tray_exit(self):
        self.stop()

    @property
    def is_running(self):
        return self.sync_server_thread.is_running

    def stop(self):
        if not self.is_running:
            return
        try:
            log.debug("Stopping synch server server")
            self.sync_server_thread.is_running = False
            self.sync_server_thread.stop()
        except Exception:
            log.warning(
                "Error has happened during Killing synchserver server",
                exc_info=True
            )

    def thread_stopped(self):
        self._is_running = False

    def reset_provider_for_file(self, file_id, provider):
        """
            Reset information about synchronization for particular 'file_id'
            and provider.
            Useful for testing or forcing file to be reuploaded.
        :param file_id: <string> file id in representation
        :param provider: <string> - 'gdrive', 'S3' etc
        :return: None
        """
        query = {
            "files._id": file_id
        }
        update = {
            "$unset":  {"files.$.sites.{}".format(provider): ""}
        }
        # it actually modifies single _id, but io.update_one not implemented
        io.update_many(
            query,
            update
        )

    def _get_success_dict(self, provider, new_file_id):
        """
            Provide success metadata ("id", "created_dt") to be stored in Db.
        :param provider: used as part of path in DB (files.sites.gdrive)
        :param new_file_id: id of created file
        :return: <dict>
        """
        val = {"files.$.sites.{}.id".format(provider): new_file_id,
               "files.$.sites.{}.created_dt".format(provider):
               datetime.utcnow()}
        return val

    def _get_error_dict(self, provider, error="", tries=""):
        """
            Provide error metadata to be stored in Db.
            Used for set (error and tries provided) or unset mode.
        :param provider: used as part of path in DB (files.sites.gdrive)
        :param error: message
        :param tries: how many times failed
        :return: <dict>
        """
        val = {"files.$.sites.{}.last_failed_dt".format(provider):
               datetime.utcnow(),
               "files.$.sites.{}.error".format(provider): error,
               "files.$.sites.{}.tries".format(provider): tries}
        return val

    def _get_tries_count(self, file, provider):
        """
            Get number of failed attempts to synch
        :param file: <dictionary> - info about specific file
        :param provider: <string> - gdrive, S3 etc
        :return: <int> - number of failed attempts
        """
        return file.get("sites", {}).get(provider, {}).get("tries", 0)


class SynchServerThread(threading.Thread):
    """
        Separate thread running synchronization server with asyncio loop.
        Stopped when tray is closed.
    """
    def __init__(self, module):
        super(SynchServerThread, self).__init__()
        self.module = module
        self.loop = None
        self.is_running = False
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)

    def run(self):
        self.is_running = True

        try:
            log.info("Starting synchserver server")
            self.loop = asyncio.new_event_loop()  # create new loop for thread
            asyncio.set_event_loop(self.loop)
            self.loop.set_default_executor(self.executor)

            asyncio.ensure_future(self.check_shutdown(), loop=self.loop)
            asyncio.ensure_future(self.sync_loop(), loop=self.loop)
            self.loop.run_forever()
        except Exception:
            log.warning(
                "Synch Server service has failed", exc_info=True
            )
        finally:
            self.loop.close()  # optional

    async def sync_loop(self):
        while self.is_running:
            import time
            from datetime import datetime
            start_time = time.time()
            sync_representations = self.module.get_sync_representations()

            task_files_to_upload = []
            files_created_info = []
            # process only unique file paths in one batch
            # multiple representation could have same file path (textures),
            # upload process can find already uploaded file and reuse same id
            processed_file_path = set()
            for provider in lib.factory.providers.keys():
                tree = lib.factory.get_provider(provider).get_tree()
                limit = lib.factory.get_provider_batch_limit(provider)
                for sync in sync_representations:
                    if limit <= 0:
                        continue
                    files = sync.get("files") or {}
                    if files:
                        for file in files:
                            # skip already processed files
                            file_path = file.get('path', '')
                            if file_path in processed_file_path:
                                continue

                            status = self.module.check_status(file, sync,
                                                              provider)

                            if status == SyncStatus.DO_UPLOAD:
                                limit -= 1
                                task_files_to_upload.append(asyncio.create_task(
                                                self.module.upload(file,
                                                                   sync,
                                                                   provider,
                                                                   tree)))
                                # store info for exception handling
                                files_created_info.append((file,
                                                           sync,
                                                           provider))
                                processed_file_path.add(file_path)
                            if status == SyncStatus.DO_DOWNLOAD:
                                limit -= 1
                                await self.module.download(file, sync, provider)
                                processed_file_path.add(file_path)
            files_created = []
            files_created = await asyncio.gather(*task_files_to_upload,
                                                 return_exceptions=True)
            for file_id, info in zip(files_created, files_created_info):
                file, representation, provider = info
                error = None
                if isinstance(file_id, BaseException):
                    error = str(file_id)
                    file_id = None
                self.module.update_db(file_id,
                                      file,
                                      representation,
                                      provider,
                                      error)

            duration = time.time() - start_time
            log.debug("One loop took {}".format(duration))
            await asyncio.sleep(60)

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
