from pype.api import config, Logger
from avalon import io

import threading
import asyncio

from enum import Enum
import datetime

from .providers import lib

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
    def __init__(self):
        self.qaction = None
        self.failed_icon = None
        self._is_running = False
        self.presets = None

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

        self.sync_server_thread = SynchServerThread(self)

    def get_sync_representations(self):
        """
            Get representations.
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
        provider = sites.get(provider) or {}
        if provider:
            created_dt = provider.get("created_dt")
            if not created_dt:
                return SyncStatus.DO_UPLOAD

        return SyncStatus.DO_NOTHING

    async def upload(self, file, representation, provider):
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
        await asyncio.sleep(0.1)
        handler = lib.factory.get_provider(provider)
        local_root = representation.get("context", {}).get("root")
        if not local_root:
            raise ValueError("Unknown local root for file {}")
        source_file = file.get("path", "").replace('{root}', local_root)
        target_root = '/{}'.format(handler.get_root_name())
        target_file = file.get("path", "").replace('{root}', target_root)

        new_file_id = handler.upload_file(source_file,
                                          target_file,
                                          overwrite=True)
        if new_file_id:
            representation_id = representation.get("_id")
            file_id = file.get("_id")
            query = {
                "_id": representation_id,
                "files._id": file_id
            }
            io.update_many(
                query
                ,
                {"$set": {"files.$.sites.gdrive.id": new_file_id,
                          "files.$.sites.gdrive.created_dt":
                          datetime.datetime.utcnow()}}
            )

        log.info("file {} uploaded {}".format(source_file, new_file_id))

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

    def run(self):
        self.is_running = True

        try:
            log.info("Starting synchserver server")
            self.loop = asyncio.new_event_loop()  # create new loop for thread
            asyncio.set_event_loop(self.loop)

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

            sync_representations = self.module.get_sync_representations()
            import time
            start_time = time.time()
            for provider in lib.factory.providers:  # TODO clumsy
                for sync in sync_representations:
                    files = sync.get("files") or {}
                    if files:
                        for file in files:
                            status = self.module.check_status(file, sync,
                                                              provider)

                            if status == SyncStatus.DO_UPLOAD:
                                await self.module.upload(file, sync, provider)
                            if status == SyncStatus.DO_DOWNLOAD:
                                await self.module.download(file, sync, provider)
            duration = time.time() - start_time
            log.info("One loop took {}".format(duration))
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
        await asyncio.sleep(0.07)
        self.loop.stop()
