class ObjAlreadyExist(Exception):
    """Is used when is created multiple objects of same RestApi class."""
    def __init__(self, cls=None, message=None):
        if not (cls and message):
            message = "RestApi object was created twice."
        elif not message:
            message = "{} object was created twice.".format(cls.__name__)
        super().__init__(message)


class AbortException(Exception):
    pass
