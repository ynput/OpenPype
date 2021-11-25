class MissingHostTemplateModule(Exception):
    """Error raised when expected module does not exists"""
    pass


class MissingTemplatePlaceholderClass(Exception):
    """ """
    pass


class MissingTemplateLoaderClass(Exception):
    """ """
    pass


class TemplateNotFound(Exception):
    """Exception raised when template does not exist."""
    pass


class TemplateProfileNotFound(Exception):
    """Exception raised when current profile
    doesn't match any template profile"""
    pass

class TemplateAlreadyImported(Exception):
    """ """
    pass


class TemplateLoadingFailed(Exception):
    """ """
    pass