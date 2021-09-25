import os


def get_ftrack_event_mongo_info():
    database_name = os.environ["OPENPYPE_DATABASE_NAME"]
    collection_name = "ftrack_events"
    return database_name, collection_name
