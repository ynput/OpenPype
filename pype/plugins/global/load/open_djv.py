import os
import subprocess
import json
from pype import lib as pypelib
from avalon import api


def get_config_data():
    path_items = [pypelib.get_presets_path(), 'djv_view', 'config.json']
    filepath = os.path.sep.join(path_items)
    data = dict()
    with open(filepath) as data_file:
        data = json.load(data_file)
    return data


def get_families():
    families = []
    paths = get_config_data().get('djv_paths', [])
    for path in paths:
        if os.path.exists(path):
            families.append("*")
            break
    return families


def get_representation():
    return get_config_data().get('file_ext', [])


class OpenInDJV(api.Loader):
    """Open Image Sequence with system default"""

    config_data = get_config_data()
    families = get_families()
    representations = get_representation()

    label = "Open in DJV"
    order = -10
    icon = "play-circle"
    color = "orange"

    def load(self, context, name, namespace, data):
        self.djv_path = None
        paths = get_config_data().get('djv_paths', [])
        for path in paths:
            if os.path.exists(path):
                self.djv_path = path
                break
        directory = os.path.dirname(self.fname)
        from avalon.vendor import clique

        pattern = clique.PATTERNS["frames"]
        files = os.listdir(directory)
        collections, remainder = clique.assemble(
            files,
            patterns=[pattern],
            minimum_items=1
        )

        if not remainder:
            seqeunce = collections[0]
            first_image = list(seqeunce)[0]
            # start = min(collections)
            # end = max(collections)
            #
            # range = (padding % start) + '-' + (padding % end)
            # filename = re.sub('%[0-9]*d', range, filename)
        else:
            first_image = self.fname
        filepath = os.path.normpath(os.path.join(directory, first_image))

        self.log.info("Opening : {}".format(filepath))

        fps = context.get('project', {}).get('data', {}).get('fps', 24)

        cmd = []
        # DJV path
        cmd.append(os.path.normpath(self.djv_path))
        # DJV Options Start ##############################################
        '''layer name'''
        # cmd.append('-file_layer (value)')
        ''' Proxy scale: 1/2, 1/4, 1/8'''
        # cmd.append('-file_proxy 1/2')
        ''' Cache: True, False.'''
        cmd.append('-file_cache True')
        ''' Start in full screen '''
        # cmd.append('-window_fullscreen')
        ''' Toolbar controls: False, True.'''
        # cmd.append("-window_toolbar False")
        ''' Window controls: False, True.'''
        # cmd.append("-window_playbar False")
        ''' Grid overlay: None, 1x1, 10x10, 100x100.'''
        # cmd.append("-view_grid None")
        ''' Heads up display: True, False.'''
        # cmd.append("-view_hud True")
        ''' Playback: Stop, Forward, Reverse.'''
        cmd.append("-playback Forward")
        ''' Frame.'''
        # cmd.append("-playback_frame (value)")
        cmd.append("-playback_speed " + str(fps))
        ''' Timer: Sleep, Timeout. Value: Sleep.'''
        # cmd.append("-playback_timer (value)")
        ''' Timer resolution (seconds): 0.001.'''
        # cmd.append("-playback_timer_resolution (value)")
        ''' Time units: Timecode, Frames.'''
        cmd.append("-time_units Frames")
        # DJV Options End ################################################

        # PATH TO COMPONENT
        cmd.append(os.path.normpath(filepath))

        # Run DJV with these commands
        subprocess.Popen(' '.join(cmd))
