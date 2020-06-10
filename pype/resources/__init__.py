import os


def get_resource(*args):
    """ Serves to simple resources access

    :param *args: should contain *subfolder* names and *filename* of
                  resource from resources folder
    :type *args: list
    """
    return os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            *args
        )
    )
