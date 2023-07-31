"""
    Helper class for automatic testing, provides dump and restore via command
    line utilities.

    Expect mongodump, mongoimport and mongorestore present at PATH
"""
import os
import pymongo
import subprocess


class DataBaseHandler:

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

    def setup_from_sql(self, database_name, sql_dir, collection=None,
                       drop=True, mode=None):
        """
            Restores 'database_name' from 'sql_url'.

            Works with directory with .json files,
            if 'collection' arg is empty, name
            of .json file is used as name of target collection.

            Args:
                database_name (str): source DB name
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
                                           database_name=database_name,
                                           collection=collection,
                                           drop=drop,
                                           mode=mode)

                print("mongoimport query:: {}".format(query))
                subprocess.run(query)

    def setup_from_sql_file(self, database_name, sql_url,
                            collection=None, drop=True, mode=None):
        """
            Restores 'database_name' from 'sql_url'.

            Works with single .json file.
            If 'collection' arg is empty, name
            of .json file is used as name of target collection.

            Args:
                database_name (str): source DB name
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
                                   database_name=database_name,
                                   collection=collection,
                                   drop=drop,
                                   mode=mode)

        print("mongoimport query:: {}".format(query))
        subprocess.run(query)

    def setup_from_dump(
        self,
        database_name,
        dump_dir,
        database_suffix,
        overwrite=False,
        collection=None,
        database_name_out=None
    ):
        """
        Restores 'database_name' from 'dump_dir'.

        Works with BSON folders exported by mongodump

        Args:
            database_name (str): source DB name
            dump_dir (str): folder with dumped subfolders
            overwrite (bool): True if overwrite target
            collection (str): name of source project
            database_name_out (str): name of target DB, if empty restores to
                source 'database_name'
        """
        database_name_out = database_name_out or database_name
        if self._database_exists(database_name_out):
            if not overwrite:
                raise RuntimeError(
                    "DB {} already exists run with overwrite=True".format(
                        database_name_out
                    )
                )
            else:
                if collection:
                    if collection in self.client[database_name_out].list_collection_names():  # noqa
                        self.client[database_name_out][collection].drop()
                else:
                    self.teardown(database_name_out)

        dir_path = os.path.join(dump_dir, database_name)
        if not os.path.exists(dir_path):
            raise RuntimeError(
                "Backup folder {} doesn't exist".format(dir_path))

        # Finf bson files to determine how to restore the database dump.
        bson_files = [x for x in os.listdir(dir_path) if x.endswith(".bson")]

        queries = []
        if bson_files:
            queries.apend(
                self._restore_query(
                    self.uri,
                    dump_dir,
                    database_name=database_name,
                    database_name_out=database_name_out + database_suffix,
                    collection=collection
                )
            )
        else:
            queries = self._restore_queries_json(
                self.uri, dir_path, database_suffix
            )

        for query in queries:
            print("mongorestore query:: {}".format(query))
            try:
                subprocess.run(query)
            except FileNotFoundError:
                raise RuntimeError(
                    "'mongorestore' or 'mongoimport' utility must be on path. "
                    "Please install it."
                )

    def teardown(self, database_name):
        """Drops 'database_name' if exists."""
        if not self._database_exists(database_name):
            print("{} doesn't exist".format(database_name))
            return

        print("Dropping {} database".format(database_name))
        self.client.drop_database(database_name)

    def backup_to_dump(
        self,
        database_name,
        dump_dir,
        overwrite=False,
        collection=None,
        json=False,
        filename=None
    ):
        """
            Helper method for running mongodump for specific 'database_name'
        """
        if not self._database_exists(database_name) and not overwrite:
            raise RuntimeError("DB {} doesn't exists".format(database_name))

        dir_path = os.path.join(dump_dir, database_name)
        if os.path.exists(dir_path) and not overwrite:
            raise RuntimeError(
                "Backup already exists. Remove existing database dumps in "
                "\"{}\" or run with overwrite=True".format(dir_path)
            )

        if json:
            query = self._dump_query_json(
                self.uri,
                dump_dir,
                database_name=database_name,
                collection=collection,
                filename=filename
            )
        else:
            query = self._dump_query(
                self.uri,
                dump_dir,
                database_name=database_name,
                collection=collection
            )
        print("Mongodump query:: {}".format(query))
        subprocess.run(query)

    def _database_exists(self, database_name):
        return database_name in self.client.list_database_names()

    def _dump_query_json(
        self,
        uri,
        output_path,
        database_name=None,
        collection=None,
        filename=None
    ):
        """Prepares dump query based on 'database_name' or 'collection'."""
        database_part = coll_part = ""
        if database_name:
            database_part = "--db={}".format(database_name)
        if collection:
            if not database_name:
                raise ValueError("database_name must be present")
            coll_part = "--collection={}".format(collection)

        if not filename:
            filename = "{}.{}.json".format(database_name, collection)

        query = (
            "mongoexport --uri=\"{}\" --jsonArray --pretty"
            " --out={} {} {}".format(
                uri,
                os.path.join(output_path, filename),
                database_part,
                coll_part
            )
        )
        return query

    def _dump_query(
        self,
        uri,
        output_path,
        database_name=None,
        collection=None
    ):
        """Prepares dump query based on 'database_name' or 'collection'."""
        database_part = coll_part = ""
        if database_name:
            database_part = "--db={}".format(database_name)
        if collection:
            if not database_name:
                raise ValueError("database_name must be present")
            coll_part = "--collection={}".format(collection)
        query = "\"{}\" --uri=\"{}\" --out={} {} {}".format(
            "mongodump", uri, output_path, database_part, coll_part
        )

        return query

    def _restore_queries_json(self, uri, dump_dir, database_suffix):
        """Prepares query for mongorestore base on arguments"""
        queries = []

        for json_file in os.listdir(dump_dir):
            database_name, collection, ext = json_file.split(".")
            queries.append(
                self._restore_query_json(
                    uri,
                    os.path.join(dump_dir, json_file),
                    database_name + database_suffix,
                    collection,
                    True
                )
            )

        return queries

    def _restore_query_json(
        self,
        uri,
        json_file,
        database_name=None,
        collection=None,
        drop=True
    ):
        """Prepares query for mongorestore base on arguments"""
        query = "mongoimport --jsonArray --uri=\"{}\" --file=\"{}\"".format(
            uri, json_file
        )

        if database_name:
            query += " --db " + database_name
        if collection:
            assert database_name, "Must provide db name too"
            query += " --collection " + collection
        if drop:
            query += " --drop"

        return query

    def _restore_query(
        self,
        uri,
        dump_dir,
        database_name=None,
        database_name_out=None,
        collection=None,
        drop=True
    ):
        """Prepares query for mongorestore base on arguments"""
        database_part = coll_part = drop_part = ""
        if database_name:
            database_part = "--nsInclude={}.* --nsFrom={}.*".format(
                database_name, database_name
            )
        if collection:
            assert database_name, "Must provide db name too"
            database_part = "--nsInclude={}.{} --nsFrom={}.{}".format(
                database_name, collection, database_name, collection
            )
        if drop:
            drop_part = "--drop"

        if database_name_out:
            collection_str = collection or '*'
            database_part += " --nsTo={}.{}".format(
                database_name_out, collection_str
            )

        query = "\"{}\" --uri=\"{}\" --dir=\"{}\" {} {} {}".format(
            "mongorestore", uri, dump_dir, database_part, coll_part, drop_part
        )

        return query

    def _import_query(
        self,
        uri,
        sql_url,
        database_name=None,
        collection=None,
        drop=True,
        mode=None
    ):

        database_part = coll_part = drop_part = mode_part = ""
        if database_name:
            database_part = "--db {}".format(database_name)
        if collection:
            assert database_name, "Must provide db name too"
            coll_part = "--collection {}".format(collection)
        if drop:
            drop_part = "--drop"
        if mode:
            mode_part = "--mode {}".format(mode)

        query = \
            "\"{}\" --legacy --uri=\"{}\" --file=\"{}\" {} {} {} {}".format(
                "mongoimport", uri, sql_url,
                database_part, coll_part, drop_part, mode_part)

        return query

# Examples
# handler = DBHandler(uri="mongodb://localhost:27017")
# #
# backup_dir = "c:\\projects\\test_zips\\test_nuke_deadline_publish\\input\\dumps"  # noqa
# # #
# handler.backup_to_dump("avalon_tests", backup_dir, True, collection="test_project")  # noqa
#handler.backup_to_dump("openpype_tests", backup_dir, True, collection="settings")  # noqa

# handler.setup_from_dump("avalon_tests", backup_dir, True, database_name_out="avalon_tests", collection="test_project")  # noqa
# handler.setup_from_sql_file("avalon_tests", "c:\\projects\\sql\\item.sql",
#                             collection="test_project",
#                             drop=False, mode="upsert")
# handler.setup_from_sql("avalon_tests", "c:\\projects\\sql",
#                        collection="test_project",
#                        drop=False, mode="upsert")
