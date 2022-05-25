class MissingHostTemplateModule(Exception):
    """Error raised when expected module does not exists"""
    pass


class MissingTemplatePlaceholderClass(Exception):
    """Error raised when module doesn't implement a placeholder class"""
    pass


class MissingTemplateLoaderClass(Exception):
    """Error raised when module doesn't implement a template loader class"""
    pass


class TemplateNotFound(Exception):
    """Exception raised when template does not exist."""
    pass


class TemplateProfileNotFound(Exception):
    """Exception raised when current profile
    doesn't match any template profile"""
    pass


class TemplateAlreadyImported(Exception):
    """Error raised when Template was already imported by host for
    this session"""
    pass


class TemplateLoadingFailed(Exception):
    """Error raised whend Template loader was unable to load the template"""
    pass