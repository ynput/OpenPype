import pymongo
import bson
import random
from datetime import datetime
import os


class TestPerformance():
    '''
        Class for testing performance of representation and their 'files'
        parts.
        Discussion is if embedded array:
                            'files' : [ {'_id': '1111', 'path':'....},
                                        {'_id'...}]
                     OR documents:
                            'files' : {
                                            '1111': {'path':'....'},
                                            '2222': {'path':'...'}
                                        }
                     is faster.

        Current results:
            without additional partial index documents is 3x faster
            With index is array 50x faster then document

        Partial index something like:
        db.getCollection('performance_test').createIndex
            ({'files._id': 1},
            {partialFilterExpresion: {'files': {'$exists': true}}})
        !DIDNT work for me, had to create manually in Compass

    '''

    MONGO_URL = 'mongodb://localhost:27017'
    MONGO_DB = 'performance_test'
    MONGO_COLLECTION = 'performance_test'

    MAX_FILE_SIZE_B = 5000
    MAX_NUMBER_OF_SITES = 50
    ROOT_DIR = "C:/projects"

    inserted_ids = []

    def __init__(self, version='array'):
        '''
            It creates and fills collection, based on value of 'version'.

        :param version: 'array' - files as embedded array,
                        'doc' - as document
        '''
        self.client = pymongo.MongoClient(self.MONGO_URL)
        self.db = self.client[self.MONGO_DB]
        self.collection_name = self.MONGO_COLLECTION

        self.version = version

        if self.version != 'array':
            self.collection_name = self.MONGO_COLLECTION + '_doc'

        self.collection = self.db[self.collection_name]

        self.ids = []  # for testing
        self.inserted_ids = []

    def prepare(self, no_of_records=100000, create_files=False):
        '''
            Produce 'no_of_records' of representations with 'files' segment.
            It depends on 'version' value in constructor, 'arrray' or 'doc'
        :return:
        '''
        print('Purging {} collection'.format(self.collection_name))
        self.collection.delete_many({})

        id = bson.objectid.ObjectId()

        insert_recs = []
        for i in range(no_of_records):
            file_id = bson.objectid.ObjectId()
            file_id2 = bson.objectid.ObjectId()
            file_id3 = bson.objectid.ObjectId()

            self.inserted_ids.extend([file_id, file_id2, file_id3])
            version_str = "v{:03d}".format(i + 1)
            file_name = "test_Cylinder_workfileLookdev_{}.mb".\
                format(version_str)

            document = {"files": self.get_files(self.version, i + 1,
                                                file_id, file_id2, file_id3,
                                                create_files)
                        ,
                        "context": {
                            "subset": "workfileLookdev",
                            "username": "petrk",
                            "task": "lookdev",
                            "family": "workfile",
                            "hierarchy": "Assets",
                            "project": {"code": "test", "name": "Test"},
                            "version": i + 1,
                            "asset": "Cylinder",
                            "representation": "mb",
                            "root": self.ROOT_DIR
                        },
                        "dependencies": [],
                        "name": "mb",
                        "parent": {"oid": '{}'.format(id)},
                        "data": {
                            "path": "C:\\projects\\test_performance\\Assets\\Cylinder\\publish\\workfile\\workfileLookdev\\{}\\{}".format(version_str, file_name),  # noqa: E501
                            "template": "{root[work]}\\{project[name]}\\{hierarchy}\\{asset}\\publish\\{family}\\{subset}\\v{version:0>3}\\{project[code]}_{asset}_{subset}_v{version:0>3}<_{output}><.{frame:0>4}>.{representation}"  # noqa: E501
                        },
                        "type": "representation",
                        "schema": "openpype:representation-2.0"
                        }

            insert_recs.append(document)

        print('Prepared {} records in {} collection'.
              format(no_of_records, self.collection_name))

        self.collection.insert_many(insert_recs)
        # TODO refactore to produce real array and not needeing ugly regex
        self.collection.insert_one({"inserted_id": self.inserted_ids})
        print('-' * 50)

    def run(self, queries=1000, loops=3):
        '''
            Run X'queries' that are searching collection Y'loops' times
        :param queries: how many times do ..find(...)
        :param loops:  loop of testing X queries
        :return: None
        '''
        print('Testing version {} on {}'.format(self.version,
                                                self.collection_name))
        print('Queries rung {} in {} loops'.format(queries, loops))

        inserted_ids = list(self.collection.
                            find({"inserted_id": {"$exists": True}}))
        import re
        self.ids = re.findall("'[0-9a-z]*'", str(inserted_ids))

        import time

        found_cnt = 0
        for _ in range(loops):
            print('Starting loop {}'.format(_))
            start = time.time()
            for _ in range(queries):
                # val = random.choice(self.ids)
                # val = val.replace("'", '')
                val = random.randint(0, 50)
                print(val)

                if (self.version == 'array'):
                    # prepared for partial index, without 'files': exists
                    # wont engage
                    found = self.collection.\
                        find({'files': {"$exists": True},
                              'files.sites.name': "local_{}".format(val)}).\
                        count()
                else:
                    key = "files.{}".format(val)
                    found = self.collection.find_one({key: {"$exists": True}})
                print("found {} records".format(found))
                # if found:
                #     found_cnt += len(list(found))

            end = time.time()
            print('duration per loop {}'.format(end - start))
            print("found_cnt {}".format(found_cnt))

    def get_files(self, mode, i, file_id, file_id2, file_id3,
                  create_files=False):
        '''
            Wrapper to decide if 'array' or document version should be used
        :param mode: 'array'|'doc'
        :param i: step number
        :param file_id: ObjectId of first dummy file
        :param file_id2: ..
        :param file_id3: ..
        :return:
        '''
        if mode == 'array':
            return self.get_files_array(i, file_id, file_id2, file_id3,
                                        create_files)
        else:
            return self.get_files_doc(i, file_id, file_id2, file_id3)

    def get_files_array(self, i, file_id, file_id2, file_id3,
                        create_files=False):
        ret = [
            {
                 "path": "{root[work]}" + "{root[work]}/test_performance/Assets/Cylinder/publish/workfile/workfileLookdev/v{:03d}/test_Cylinder_A_workfileLookdev_v{:03d}.dat".format(i, i),  # noqa: E501
                 "_id": '{}'.format(file_id),
                 "hash": "temphash",
                 "sites": self.get_sites(self.MAX_NUMBER_OF_SITES),
                 "size": random.randint(0, self.MAX_FILE_SIZE_B)
            },
            {
                "path": "{root[work]}" + "/test_performance/Assets/Cylinder/publish/workfile/workfileLookdev/v{:03d}/test_Cylinder_B_workfileLookdev_v{:03d}.dat".format(i, i),  # noqa: E501
                "_id": '{}'.format(file_id2),
                "hash": "temphash",
                "sites": self.get_sites(self.MAX_NUMBER_OF_SITES),
                "size": random.randint(0, self.MAX_FILE_SIZE_B)
            },
            {
                "path": "{root[work]}" + "/test_performance/Assets/Cylinder/publish/workfile/workfileLookdev/v{:03d}/test_Cylinder_C_workfileLookdev_v{:03d}.dat".format(i, i),  # noqa: E501
                "_id": '{}'.format(file_id3),
                "hash": "temphash",
                "sites": self.get_sites(self.MAX_NUMBER_OF_SITES),
                "size": random.randint(0, self.MAX_FILE_SIZE_B)
            }

            ]
        if create_files:
            for f in ret:
                path = f.get("path").replace("{root[work]}", self.ROOT_DIR)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'wb') as fp:
                    fp.write(os.urandom(f.get("size")))

        return ret

    def get_files_doc(self, i, file_id, file_id2, file_id3):
        ret = {}
        ret['{}'.format(file_id)] = {
            "path": "{root[work]}" +
                    "/test_performance/Assets/Cylinder/publish/workfile/workfileLookdev/"  # noqa: E501
                    "v{:03d}/test_CylinderA_workfileLookdev_v{:03d}.mb".format(i, i),  # noqa: E501
            "hash": "temphash",
            "sites": ["studio"],
            "size": 87236
        }

        ret['{}'.format(file_id2)] = {
            "path": "{root[work]}" +
                    "/test_performance/Assets/Cylinder/publish/workfile/workfileLookdev/"  # noqa: E501
                    "v{:03d}/test_CylinderB_workfileLookdev_v{:03d}.mb".format(i, i),  # noqa: E501
            "hash": "temphash",
            "sites": ["studio"],
            "size": 87236
        }
        ret['{}'.format(file_id3)] = {
            "path": "{root[work]}" +
                    "/test_performance/Assets/Cylinder/publish/workfile/workfileLookdev/"  # noqa: E501
                    "v{:03d}/test_CylinderC_workfileLookdev_v{:03d}.mb".format(i, i),  # noqa: E501
            "hash": "temphash",
            "sites": ["studio"],
            "size": 87236
        }

        return ret

    def get_sites(self, number_of_sites=50):
        """
            Return array of sites declaration.
            Currently on 1st site has "created_dt" fillled, which should
            trigger upload to 'gdrive' site.
            'gdrive' site is appended, its destination for syncing for
            Sync Server
        Args:
            number_of_sites:

        Returns:

        """
        sites = []
        for i in range(number_of_sites):
            site = {'name': "local_{}".format(i)}
            # do not create null 'created_dt' field, Mongo doesnt like it
            if i == 0:
                site['created_dt'] = datetime.now()

            sites.append(site)

        sites.append({'name': "gdrive"})

        return sites


if __name__ == '__main__':
    tp = TestPerformance('array')
    tp.prepare(no_of_records=10000, create_files=True)
    # tp.run(10, 3)

    # print('-'*50)
    #
    # tp = TestPerformance('doc')
    # tp.prepare()  # enable to prepare data
    # tp.run(1000, 3)
