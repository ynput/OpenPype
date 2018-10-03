from .lib import *


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
