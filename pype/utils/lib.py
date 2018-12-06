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

def load_capture_preset(path):
    import capture_gui
    import capture

    path = path
    preset = capture_gui.lib.load_json(path)
    print preset

    options = dict()

    # CODEC
    id = 'Codec'
    for key in preset[id]:
        options[str(key)] = preset[id][key]

    # GENERIC
    id = 'Generic'
    for key in preset[id]:
        if key.startswith('isolate'):
            pass
            # options['isolate'] = preset[id][key]
        else:
            options[str(key)] = preset[id][key]

    # RESOLUTION
    id = 'Resolution'
    options['height'] = preset[id]['height']
    options['width'] = preset[id]['width']

    # DISPLAY OPTIONS
    id = 'Display Options'
    disp_options = {}
    for key in preset['Display Options']:
        if key.startswith('background'):
            disp_options[key] = preset['Display Options'][key]
        else:
            disp_options['displayGradient'] = True

    options['display_options'] = disp_options

    # VIEWPORT OPTIONS
    temp_options = {}
    id = 'Renderer'
    for key in preset[id]:
        temp_options[str(key)] = preset[id][key]

    temp_options2 = {}
    id = 'Viewport Options'
    light_options = {0: "default",
                        1: 'all',
                        2: 'selected',
                        3: 'flat',
                        4: 'nolights'}
    for key in preset[id]:
        if key == 'high_quality':
            temp_options2['multiSampleEnable'] = True
            temp_options2['multiSampleCount'] = 4
            temp_options2['textureMaxResolution'] = 512
            temp_options2['enableTextureMaxRes'] = True

        if key == 'alphaCut':
            temp_options2['transparencyAlgorithm'] = 5
            temp_options2['transparencyQuality'] = 1

        if key == 'headsUpDisplay':
            temp_options['headsUpDisplay'] = True

        if key == 'displayLights':
            temp_options[str(key)] = light_options[preset[id][key]]
        else:
            temp_options[str(key)] = preset[id][key]

    for key in ['override_viewport_options', 'high_quality', 'alphaCut']:
        temp_options.pop(key, None)

    options['viewport_options'] = temp_options
    options['viewport2_options'] = temp_options2

    # use active sound track
    scene = capture.parse_active_scene()
    options['sound'] = scene['sound']
    cam_options = dict()
    cam_options['overscan'] = 1.0
    cam_options['displayFieldChart'] = False
    cam_options['displayFilmGate'] = False
    cam_options['displayFilmOrigin'] = False
    cam_options['displayFilmPivot'] = False
    cam_options['displayGateMask'] = False
    cam_options['displayResolution'] = False
    cam_options['displaySafeAction'] = False
    cam_options['displaySafeTitle'] = False

    # options['display_options'] = temp_options

    return options
