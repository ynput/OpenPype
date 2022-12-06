"""
    Helper class for automatic testing, provides dump and restore via command
    line utilities.

    Expect mongodump, mongoimport and mongorestore present at PATH
"""
import os
import pymongo
import subprocess


class DBHandler:

    def __init__(self, uri=None, host=None, port=None,
                 user=None, password=None):
        """'uri' or rest of separate credentials"""
        if uri:
            self.uri = uri
        if host:
            if all([user, password]):
                host = "{}:{}@{}".format(user, password, host)
            self.uri = 'mongodb://{}:{}'.format(host, port or 27017)

        assert self.uri, "Must have uri to MongoDB"
        self.client = pymongo.MongoClient(uri)
        self.db = None

    def setup_empty(self, name):
        # not much sense
        self.db = self.client[name]

    def setup_from_sql(self, db_name, sql_dir, collection=None,
                       drop=True, mode=None):
        """
            Restores 'db_name' from 'sql_url'.

            Works with directory with .json files,
            if 'collection' arg is empty, name
            of .json file is used as name of target collection.

            Args:
                db_name (str): source DB name
                sql_dir (str): folder with json files
                collection (str): if all sql files are meant for single coll.
                drop (bool): True if drop whole collection
                mode (str): "insert" - fails on duplicates
                            "upsert" - modifies existing
                            "merge" - updates existing
                            "delete" - removes in DB present if file
        """
        if not os.path.exists(sql_dir):
            raise RuntimeError(
                "Backup folder {} doesn't exist".format(sql_dir))

        for (dirpath, _dirnames, filenames) in os.walk(sql_dir):
            for file_name in filenames:
                sql_url = os.path.join(dirpath, file_name)
                query = self._import_query(self.uri, sql_url,
                                           db_name=db_name,
                                           collection=collection,
                                           drop=drop,
                                           mode=mode)

                print("mongoimport query:: {}".format(query))
                subprocess.run(query)

    def setup_from_sql_file(self, db_name, sql_url,
                            collection=None, drop=True, mode=None):
        """
            Restores 'db_name' from 'sql_url'.

            Works with single .json file.
            If 'collection' arg is empty, name
            of .json file is used as name of target collection.

            Args:
                db_name (str): source DB name
                sql_file (str): folder with json files
                collection (str): name of target collection
                drop (bool): True if drop collection
                mode (str): "insert" - fails on duplicates
                            "upsert" - modifies existing
                            "merge" - updates existing
                            "delete" - removes in DB present if file
        """
        if not os.path.exists(sql_url):
            raise RuntimeError(
                "Sql file {} doesn't exist".format(sql_url))

        query = self._import_query(self.uri, sql_url,
                                   db_name=db_name,
                                   collection=collection,
                                   drop=drop,
                                   mode=mode)

        print("mongoimport query:: {}".format(query))
        subprocess.run(query)

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
        if self._db_exists(db_name_out):
            if not overwrite:
                raise RuntimeError("DB {} already exists".format(db_name_out) +
                                   "Run with overwrite=True")
            else:
                if collection:
                    if collection in self.client[db_name_out].list_collection_names():  # noqa
                        self.client[db_name_out][collection].drop()
                else:
                    self.teardown(db_name_out)

        dir_path = os.path.join(dump_dir, db_name)
        if not os.path.exists(dir_path):
            raise RuntimeError(
                "Backup folder {} doesn't exist".format(dir_path))

        query = self._restore_query(self.uri, dump_dir,
                                    db_name=db_name, db_name_out=db_name_out,
                                    collection=collection)
        print("mongorestore query:: {}".format(query))
        try:
            subprocess.run(query)
        except FileNotFoundError:
            raise RuntimeError("'mongorestore' utility must be on path."
                               "Please install it.")

    def teardown(self, db_name):
        """Drops 'db_name' if exists."""
        if not self._db_exists(db_name):
            print("{} doesn't exist".format(db_name))
            return

        print("Dropping {} database".format(db_name))
        self.client.drop_database(db_name)

    def backup_to_dump(self, db_name, dump_dir, overwrite=False,
                       collection=None):
        """
            Helper method for running mongodump for specific 'db_name'
        """
        if not self._db_exists(db_name) and not overwrite:
            raise RuntimeError("DB {} doesn't exists".format(db_name))

        dir_path = os.path.join(dump_dir, db_name)
        if os.path.exists(dir_path) and not overwrite:
            raise RuntimeError("Backup already exists, "
                               "run with overwrite=True")

        query = self._dump_query(self.uri, dump_dir,
                                 db_name=db_name, collection=collection)
        print("Mongodump query:: {}".format(query))
        subprocess.run(query)

    def _db_exists(self, db_name):
        return db_name in self.client.list_database_names()

    def _dump_query(self, uri, output_path, db_name=None, collection=None):
        """Prepares dump query based on 'db_name' or 'collection'."""
        db_part = coll_part = ""
        if db_name:
            db_part = "--db={}".format(db_name)
        if collection:
            if not db_name:
                raise ValueError("db_name must be present")
            coll_part = "--collection={}".format(collection)
        query = "\"{}\" --uri=\"{}\" --out={} {} {}".format(
            "mongodump", uri, output_path, db_part, coll_part
        )

        return query

    def _restore_query(self, uri, dump_dir,
                       db_name=None, db_name_out=None,
                       collection=None, drop=True):
        """Prepares query for mongorestore base on arguments"""
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
            collection_str = collection or '*'
            db_part += " --nsTo={}.{}".format(db_name_out, collection_str)

        query = "\"{}\" --uri=\"{}\" --dir=\"{}\" {} {} {}".format(
            "mongorestore", uri, dump_dir, db_part, coll_part, drop_part
        )

        return query

    def _import_query(self, uri, sql_url,
                      db_name=None,
                      collection=None, drop=True, mode=None):

        db_part = coll_part = drop_part = mode_part = ""
        if db_name:
            db_part = "--db {}".format(db_name)
        if collection:
            assert db_name, "Must provide db name too"
            coll_part = "--collection {}".format(collection)
        if drop:
            drop_part = "--drop"
        if mode:
            mode_part = "--mode {}".format(mode)

        query = \
            "\"{}\" --legacy --uri=\"{}\" --file=\"{}\" {} {} {} {}".format(
                "mongoimport", uri, sql_url,
                db_part, coll_part, drop_part, mode_part)

        return query

# Examples
# handler = DBHandler(uri="mongodb://localhost:27017")
# #
# backup_dir = "c:\\projects\\test_zips\\test_nuke_deadline_publish\\input\\dumps"  # noqa
# # #
# handler.backup_to_dump("avalon_tests", backup_dir, True, collection="test_project")  # noqa
#handler.backup_to_dump("openpype_tests", backup_dir, True, collection="settings")  # noqa

# handler.setup_from_dump("avalon_tests", backup_dir, True, db_name_out="avalon_tests", collection="test_project")  # noqa
# handler.setup_from_sql_file("avalon_tests", "c:\\projects\\sql\\item.sql",
#                             collection="test_project",
#                             drop=False, mode="upsert")
# handler.setup_from_sql("avalon_tests", "c:\\projects\\sql",
#                        collection="test_project",
#                        drop=False, mode="upsert")
