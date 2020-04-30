import shutil
import re
import pyblish.api


class VersionUpScene(pyblish.api.ContextPlugin):
    order = pyblish.api.IntegratorOrder
    label = 'Version Up Scene'
    families = ['scene']
    optional = True
    active = True

    def process(self, context):
        current_file = context.data.get('currentFile')
        v_up = get_version_up(current_file)
        self.log.debug('Current file is: {}'.format(current_file))
        self.log.debug('Version up: {}'.format(v_up))

        shutil.copy2(current_file, v_up)
        self.log.info('Scene saved into new version: {}'.format(v_up))


def version_get(string, prefix, suffix=None):
    """Extract version information from filenames used by DD (and Weta, apparently)
    These are _v# or /v# or .v# where v is a prefix string, in our case
    we use "v" for render version and "c" for camera track version.
    See the version.py and camera.py plugins for usage."""

    if string is None:
        raise ValueError("Empty version string - no match")

    regex = r"[/_.]{}\d+".format(prefix)
    matches = re.findall(regex, string, re.IGNORECASE)
    if not len(matches):
        msg = f"No `_{prefix}#` found in `{string}`"
        raise ValueError(msg)
    return (matches[-1:][0][1], re.search(r"\d+", matches[-1:][0]).group())


def version_set(string, prefix, oldintval, newintval):
    """Changes version information from filenames used by DD (and Weta, apparently)
    These are _v# or /v# or .v# where v is a prefix string, in our case
    we use "v" for render version and "c" for camera track version.
    See the version.py and camera.py plugins for usage."""

    regex = r"[/_.]{}\d+".format(prefix)
    matches = re.findall(regex, string, re.IGNORECASE)
    if not len(matches):
        return ""

    # Filter to retain only version strings with matching numbers
    matches = filter(lambda s: int(s[2:]) == oldintval, matches)

    # Replace all version strings with matching numbers
    for match in matches:
        # use expression instead of expr so 0 prefix does not make octal
        fmt = "%%(#)0%dd" % (len(match) - 2)
        newfullvalue = match[0] + prefix + str(fmt % {"#": newintval})
        string = re.sub(match, newfullvalue, string)
    return string


def get_version_up(path):
    """ Returns the next version of the path """

    (prefix, v) = version_get(path, 'v')
    v = int(v)
    return version_set(path, prefix, v, v + 1)
