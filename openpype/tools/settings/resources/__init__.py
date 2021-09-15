import os


RESOURCES_DIR = os.path.dirname(os.path.abspath(__file__))


def get_resource(*args):
    return os.path.normpath(os.path.join(RESOURCES_DIR, *args))
