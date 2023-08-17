

class P4BaseException(Exception):
    pass


class P4AttributeError(P4BaseException):
    pass


class P4PathDoesNotExistError(P4BaseException):
    pass


class P4ServerConnectionError(P4BaseException):
    pass


class P4ExclusiveCheckoutError(P4BaseException):
    def __init__(self, files):
        # type: (list[str]) -> None
        files_str = "\n - ".join(files)
        super().__init__(f"The following files are exclusively checked out:\n - {files_str}")


class P4UnsafeOfflineCommandError(P4BaseException):
    def __init__(self, action):
        # type: (str) -> None
        super().__init__(f"This action is not safe to run offline: {action}")



class P4Exceptions:
    P4BaseException = P4BaseException
    P4AttributeError = P4AttributeError
    P4PathDoesNotExistError = P4PathDoesNotExistError
    P4ServerConnectionError = P4ServerConnectionError
