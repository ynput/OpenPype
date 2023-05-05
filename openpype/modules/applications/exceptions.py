class ApplicationNotFound(Exception):
    """Application was not found in ApplicationManager by name."""

    def __init__(self, app_name):
        self.app_name = app_name
        super(ApplicationNotFound, self).__init__(
            "Application \"{}\" was not found.".format(app_name)
        )


class ApplicationExecutableNotFound(Exception):
    """Defined executable paths are not available on the machine."""

    def __init__(self, application):
        self.application = application
        details = None
        if not application.executables:
            msg = (
                "Executable paths for application \"{}\"({}) are not set."
            )
        else:
            msg = (
                "Defined executable paths for application \"{}\"({})"
                " are not available on this machine."
            )
            details = "Defined paths:"
            for executable in application.executables:
                details += "\n- " + executable.executable_path

        self.msg = msg.format(application.full_label, application.full_name)
        self.details = details

        exc_mgs = str(self.msg)
        if details:
            # Is good idea to pass new line symbol to exception message?
            exc_mgs += "\n" + details
        self.exc_msg = exc_mgs
        super(ApplicationExecutableNotFound, self).__init__(exc_mgs)


class ApplicationLaunchFailed(Exception):
    """Application launch failed due to known reason.

    Message should be self explanatory as traceback won't be shown.
    """

    pass


class MissingRequiredKey(KeyError):
    pass
