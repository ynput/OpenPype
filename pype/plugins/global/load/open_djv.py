import os
import subprocess
from avalon import api


def existing_djv_path():
    djv_paths = os.environ.get("DJV_PATH") or ""
    for path in djv_paths.split(os.pathsep):
        if os.path.exists(path):
            return path
    return None


class OpenInDJV(api.Loader):
    """Open Image Sequence with system default"""

    djv_path = existing_djv_path()
    families = ["*"] if djv_path else []
    representations = [
        "cin", "dpx", "avi", "dv", "gif", "flv", "mkv", "mov", "mpg", "mpeg",
        "mp4", "m4v", "mxf", "iff", "z", "ifl", "jpeg", "jpg", "jfif", "lut",
        "1dl", "exr", "pic", "png", "ppm", "pnm", "pgm", "pbm", "rla", "rpf",
        "sgi", "rgba", "rgb", "bw", "tga", "tiff", "tif", "img"
    ]

    label = "Open in DJV"
    order = -10
    icon = "play-circle"
    color = "orange"

    def load(self, context, name, namespace, data):
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
