import re
import tempfile
import json
import os
import sys
import pyblish.api

print 'pyblish_utils loaded'


def save_preset(path, preset):
    """Save options to path"""
    with open(path, "w") as f:
        json.dump(preset, f)


def load_preset(path):
    """Load options json from path"""
    with open(path, "r") as f:
        return json.load(f)


def temp_dir(context):
    """Provide a temporary directory in which to store extracted files"""
    extract_dir = context.data('extractDir')

    if not extract_dir:
        extract_dir = tempfile.mkdtemp()
        context.set_data('extractDir', value=extract_dir)

    return extract_dir


def version_get(string, prefix, suffix=None):
    """Extract version information from filenames.  Code from Foundry's nukescripts.version_get()"""

    if string is None:
        raise ValueError, "Empty version string - no match"

    regex = "[/_.]" + prefix + "\d+"
    matches = re.findall(regex, string, re.IGNORECASE)
    if not len(matches):
        msg = "No \"_" + prefix + "#\" found in \"" + string + "\""
        raise ValueError, msg
    return (matches[-1:][0][1], re.search("\d+", matches[-1:][0]).group())


def version_set(string, prefix, oldintval, newintval):
    """Changes version information from filenames. Code from Foundry's nukescripts.version_set()"""

    regex = "[/_.]" + prefix + "\d+"
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


def version_up(string):

    try:
        (prefix, v) = version_get(string, 'v')
        v = int(v)
        file = version_set(string, prefix, v, v + 1)
    except:
        raise ValueError, 'Unable to version up File'

    return file


def open_folder(path):
    """Provide a temporary directory in which to store extracted files"""
    import subprocess
    path = os.path.abspath(path)
    if sys.platform == 'win32':
        subprocess.Popen('explorer "%s"' % path)
    elif sys.platform == 'darwin':  # macOS
        subprocess.Popen(['open', path])
    else:  # linux
        try:
            subprocess.Popen(['xdg-open', path])
        except OSError:
            raise OSError('unsupported xdg-open call??')


def filter_instances(context, plugin):
    """Provide a temporary directory in which to store extracted files"""
    # Get the errored instances
    allInstances = []
    for result in context.data["results"]:
        if (result["instance"] is not None and
           result["instance"] not in allInstances):
            allInstances.append(result["instance"])

    # Apply pyblish.logic to get the instances for the plug-in
    instances = pyblish.api.instances_by_plugin(allInstances, plugin)

    return instances
