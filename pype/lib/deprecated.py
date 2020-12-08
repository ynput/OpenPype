import os


def get_avalon_database():
    """Mongo database used in avalon's io.

    * Function is not used in pype 3.0 where was replaced with usage of
    AvalonMongoDB.
    """
    from avalon import io
    if io._database is None:
        set_io_database()
    return io._database


def set_io_database():
    """Set avalon's io context with environemnts.

    * Function is not used in pype 3.0 where was replaced with usage of
    AvalonMongoDB.
    """
    from avalon import io
    required_keys = ["AVALON_PROJECT", "AVALON_ASSET", "AVALON_SILO"]
    for key in required_keys:
        os.environ[key] = os.environ.get(key, "")
    io.install()
