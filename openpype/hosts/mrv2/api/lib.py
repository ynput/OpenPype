import re

from mrv2 import cmd


def get_version():
    """Return major, minor, patch integer version of mrv2 application.

    Returns:
        tuple: Three integers (major, minor, path)
    """

    if not hasattr(cmd, "getVersion"):
        # `cmd.getVersion` was added around 0.8.0.
        # Assume it's the last version before `getVersion` got added
        return 0, 7, 9

    version = cmd.getVersion()
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError("Unable to retrieve major.minor.patch from version: "
                         "{}".format(version))
    major, minor, patch = tuple(int(x) for x in match.groups())
    return major, minor, patch
