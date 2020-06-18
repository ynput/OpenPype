import pymongo
import bson
import random


class TestPerformance():
    '''
        Class for testing performance of representation and their 'files' parts.
        Discussion is if embedded array:
                            'files' : [ {'_id': '1111', 'path':'....},
                                        {'_id'...}]
                     OR documents:
                            'files' : {
                                            '1111': {'path':'....'},
                                            '2222': {'path':'...'}
                                        }
                     is faster.

        Current results: without additional partial index documents is 3x faster
            With index is array 50x faster then document

        Partial index something like:
        db.getCollection('performance_test').createIndex
            ({'files._id': 1},
            {partialFilterExpresion: {'files': {'$exists': true}})
        !DIDNT work for me, had to create manually in Compass

    '''

    MONGO_URL = 'mongodb://localhost:27017'
    MONGO_DB = 'performance_test'
    MONGO_COLLECTION = 'performance_test'

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

    def prepare(self, no_of_records=100000):
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

            document = {"files": self.get_files(self.version, i,
                                                file_id, file_id2, file_id3)
                        ,
                        "context": {
                            "subset": "workfileLookdev",
                            "username": "petrk",
                            "task": "lookdev",
                            "family": "workfile",
                            "hierarchy": "Assets",
                            "project": {"code": "test", "name": "Test"},
                            "version": 1,
                            "asset": "Cylinder",
                            "representation": "mb",
                            "root": "C:/projects"
                        },
                        "dependencies": [],
                        "name": "mb",
                        "parent": {"oid": '{}'.format(id)},
                        "data": {
                            "path": "C:\\projects\\Test\\Assets\\Cylinder\\publish\\workfile\\workfileLookdev\\v001\\test_Cylinder_workfileLookdev_v001.mb",
                            "template": "{root}\\{project[name]}\\{hierarchy}\\{asset}\\publish\\{family}\\{subset}\\v{version:0>3}\\{project[code]}_{asset}_{subset}_v{version:0>3}<_{output}><.{frame:0>4}>.{representation}"
                        },
                        "type": "representation",
                        "schema": "pype:representation-2.0"
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

        inserted_ids = list(self.collection.
                            find({"inserted_id": {"$exists": True}}))
        import re
        self.ids = re.findall("'[0-9a-z]*'", str(inserted_ids))

        import time

        found_cnt = 0
        for _ in range(loops):
            start = time.time()
            for _ in range(queries):
                val = random.choice(self.ids)
                val = val.replace("'", '')

                if (self.version == 'array'):
                    # prepared for partial index, without 'files': exists
                    # wont engage
                    found = self.collection.\
                        find_one({'files': {"$exists": True},
                                  'files._id': "{}".format(val)})
                else:
                    key = "files.{}".format(val)
                    found = self.collection.find_one({key: {"$exists": True}})
                if found:
                    found_cnt += 1

            end = time.time()
            print('duration per loop {}'.format(end - start))
            print("found_cnt {}".format(found_cnt))

    def get_files(self, mode, i, file_id, file_id2, file_id3):
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
            return self.get_files_array(i, file_id, file_id2, file_id3)
        else:
            return self.get_files_doc(i, file_id, file_id2, file_id3)

    def get_files_array(self, i, file_id, file_id2, file_id3):
        return [
            {
                 "path": "c:/Test/Assets/Cylinder/publish/workfile/"
                         "workfileLookdev/v001/"
                         "test_CylinderA_workfileLookdev_v{0:03}.mb".format(i),
                 "_id": '{}'.format(file_id),
                 "hash": "temphash",
                 "sites": ["studio"],
                 "size":87236
            },
            {
                "path": "c:/Test/Assets/Cylinder/publish/workfile/"
                        "workfileLookdev/v001/"
                        "test_CylinderB_workfileLookdev_v{0:03}.mb".format(i),
                "_id": '{}'.format(file_id2),
                "hash": "temphash",
                "sites": ["studio"],
                "size": 87236
            },
            {
                "path": "c:/Test/Assets/Cylinder/publish/workfile/"
                        "workfileLookdev/v001/"
                        "test_CylinderC_workfileLookdev_v{0:03}.mb".format(i),
                "_id": '{}'.format(file_id3),
                "hash": "temphash",
                "sites": ["studio"],
                "size": 87236
            }

            ]

    def get_files_doc(self, i, file_id, file_id2, file_id3):
        ret = {}
        ret['{}'.format(file_id)] = {
            "path": "c:/Test/Assets/Cylinder/publish/workfile/workfileLookdev/"
                    "v001/test_CylinderA_workfileLookdev_v{0:03}.mb".format(i),
            "hash": "temphash",
            "sites": ["studio"],
            "size": 87236
        }

        ret['{}'.format(file_id2)] = {
            "path": "c:/Test/Assets/Cylinder/publish/workfile/workfileLookdev/"
                    "v001/test_CylinderB_workfileLookdev_v{0:03}.mb".format(i),
            "hash": "temphash",
            "sites": ["studio"],
            "size": 87236
        }
        ret['{}'.format(file_id3)] = {
            "path": "c:/Test/Assets/Cylinder/publish/workfile/workfileLookdev/"
                    "v001/test_CylinderC_workfileLookdev_v{0:03}.mb".format(i),
            "hash": "temphash",
            "sites": ["studio"],
            "size": 87236
        }

        return ret


if __name__ == '__main__':
    tp = TestPerformance('array')
    tp.prepare()  # enable to prepare data
    tp.run(1000, 3)

    print('-'*50)

    tp = TestPerformance('doc')
    tp.prepare()  # enable to prepare data
    tp.run(1000, 3)
