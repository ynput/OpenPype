"""
    Helper class for automatic testing, provides dump and restore via command
    line utilities.

    Expect mongodump and mongorestore present at MONGODB_UTILS_DIR
"""
import os
import pymongo
import subprocess


class DBHandler():

    # vendorize ??
    MONGODB_UTILS_DIR = "c:\\Program Files\\MongoDB\\Server\\4.4\\bin"

    def __init__(self, uri=None, host=None, port=None, 
                 user=None, password=None):
        """'uri' or rest of separate credentials"""
        if uri:
            self.uri = uri
        if host:
            if all([user, password]):
                host = "{}:{}@{}".format(user, password, host)
            uri = 'mongodb://{}:{}'.format(host, port or 27017)

        assert uri, "Must have uri to MongoDB"
        self.client = pymongo.MongoClient(uri)
        self.db = None

    def setup_empty(self, name):
        # not much sense
        self.db = self.client[name]

    def setup_from_dump(self, db_name, dump_dir, overwrite=False,
                        collection=None, db_name_out=None):
        """
            Restores 'db_name' from 'dump_dir'.

            Works with BSON folders exported by mongodump

            Args:
                db_name (str): source DB name
                dump_dir (str): folder with dumped subfolders
                overwrite (bool): True if overwrite target
                collection (str): name of source project
                db_name_out (str): name of target DB, if empty restores to
                    source 'db_name'
        """
        db_name_out = db_name_out or db_name
        if self._db_exists(db_name) and not overwrite:
            raise RuntimeError("DB {} already exists".format(db_name_out) +
                               "Run with overwrite=True")

        dir_path = os.path.join(dump_dir, db_name)
        if not os.path.exists(dir_path):
            raise RuntimeError(
                "Backup folder {} doesn't exist".format(dir_path))

        query = self._restore_query(self.uri, dump_dir,
                                    db_name=db_name, db_name_out=db_name_out,
                                    collection=collection)
        print("mongorestore query:: {}".format(query))
        subprocess.run(query)

    def teardown(self, db_name):
        """Drops 'db_name' if exists."""
        if not self._db_exists(db_name):
            print("{} doesn't exist".format(db_name))
            return

        print("Dropping {} database".format(db_name))
        self.client.drop_database(db_name)

    def backup_to_dump(self, db_name, dump_dir, overwrite=False):
        """
            Helper class for running mongodump for specific 'db_name'
        """
        if not self._db_exists(db_name) and not overwrite:
            raise RuntimeError("DB {} doesn't exists".format(db_name))

        dir_path = os.path.join(dump_dir, db_name)
        if os.path.exists(dir_path) and not overwrite:
            raise RuntimeError("Backup already exists, "
                               "run with overwrite=True")

        query = self._dump_query(self.uri, dump_dir, db_name=db_name)
        print("Mongodump query:: {}".format(query))
        subprocess.run(query)

    def _db_exists(self, db_name):
        return db_name in self.client.list_database_names()

    def _dump_query(self, uri,
                       output_path,
                       db_name=None, collection=None):

        utility_path = os.path.join(self.MONGODB_UTILS_DIR, "mongodump")

        db_part = coll_part = ""
        if db_name:
            db_part = "--db={}".format(db_name)
        if collection:
            if not db_name:
                raise ValueError("db_name must be present")
            coll_part = "--nsInclude={}.{}".format(db_name, collection)
        query = "\"{}\" --uri=\"{}\" --out={} {} {}".format(
            utility_path, uri, output_path, db_part, coll_part
        )

        return query

    def _restore_query(self, uri, dump_dir,
                       db_name=None, db_name_out=None,
                       collection=None, drop=True):

        utility_path = os.path.join(self.MONGODB_UTILS_DIR, "mongorestore")

        db_part = coll_part = drop_part = ""
        if db_name:
            db_part = "--nsInclude={}.* --nsFrom={}.*".format(db_name, db_name)
        if collection:
            assert db_name, "Must provide db name too"
            db_part = "--nsInclude={}.{} --nsFrom={}.{}".format(db_name,
                                                                collection,
                                                                db_name,
                                                                collection)
        if drop:
            drop_part = "--drop"

        if db_name_out:
            db_part += " --nsTo={}.*".format(db_name_out)

        query = "\"{}\" --uri=\"{}\" --dir=\"{}\" {} {} {}".format(
            utility_path, uri, dump_dir, db_part, coll_part, drop_part
        )

        return query

# handler = DBHandler(uri="mongodb://localhost:27017")
#
# backup_dir = "c:\\projects\\dumps"
#
# handler.backup_to_dump("openpype", backup_dir, True)
# handler.setup_from_dump("test_db", backup_dir, True)
