import requests
import os


def requests_post(*args, **kwargs):
    """Wrap request post method.

    Disabling SSL certificate validation if ``DONT_VERIFY_SSL`` environment
    variable is found. This is useful when Deadline or Muster server are
    running with self-signed certificates and their certificate is not
    added to trusted certificates on client machines.

    Warning:
        Disabling SSL certificate validation is defeating one line
        of defense SSL is providing and it is not recommended.

    """
    if "verify" not in kwargs:
        kwargs["verify"] = not os.getenv("OPENPYPE_DONT_VERIFY_SSL", True)
    return requests.post(*args, **kwargs)


def requests_get(*args, **kwargs):
    """Wrap request get method.

    Disabling SSL certificate validation if ``DONT_VERIFY_SSL`` environment
    variable is found. This is useful when Deadline or Muster server are
    running with self-signed certificates and their certificate is not
    added to trusted certificates on client machines.

    Warning:
        Disabling SSL certificate validation is defeating one line
        of defense SSL is providing and it is not recommended.

    """
    if "verify" not in kwargs:
        kwargs["verify"] = not os.getenv("OPENPYPE_DONT_VERIFY_SSL", True)
    return requests.get(*args, **kwargs)
