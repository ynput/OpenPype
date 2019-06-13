from pype.ftrack import BaseAction
import os
import sys
import json
import subprocess
from pype.vendor import ftrack_api
import logging
import operator
import re
from pypeapp import Logger, config

log = Logger().get_logger(__name__)


class RVAction(BaseAction):
    """ Launch RV action """
    identifier = "rv.launch.action"
    label = "rv"
    description = "rv Launcher"
    icon = '{}/ftrack/action_icons/RV.png'.format(
        os.environ.get('PYPE_STATICS_SERVER', '')
    )
    type = 'Application'

    def __init__(self, session):
        """ Constructor

            :param session: ftrack Session
            :type session: :class:`ftrack_api.Session`
        """
        super().__init__(session)
        self.rv_path = None
        self.config_data = None

        # RV_HOME should be set if properly installed
        if os.environ.get('RV_HOME'):
            self.rv_path = os.path.join(
                os.environ.get('RV_HOME'),
                'bin',
                'rv'
            )
        else:
            # if not, fallback to config file location
            self.config_data = config.get_presets()['rv']['config']
            self.set_rv_path()

        if self.rv_path is None:
            return

        self.allowed_types = self.config_data.get(
            'file_ext', ["img", "mov", "exr"]
        )

    def discover(self, session, entities, event):
        """Return available actions based on *event*. """
        selection = event["data"].get("selection", [])
        if len(selection) != 1:
            return False

        entityType = selection[0].get("entityType", None)
        if entityType in ["assetversion", "task"]:
            return True
        return False

    def set_rv_path(self):
        self.rv_path = self.config_data.get("rv_path")

    def register(self):
        assert (self.rv_path is not None), (
            'RV is not installed'
            ' or paths in presets are not set correctly'
        )
        super().register()

    def interface(self, session, entities, event):
        if event['data'].get('values', {}):
            return

        entity = entities[0]
        versions = []

        entity_type = entity.entity_type.lower()
        if entity_type == "assetversion":
            if (
                entity[
                    'components'
                ][0]['file_type'][1:] in self.allowed_types
            ):
                versions.append(entity)
        else:
            master_entity = entity
            if entity_type == "task":
                master_entity = entity['parent']

            for asset in master_entity['assets']:
                for version in asset['versions']:
                    # Get only AssetVersion of selected task
                    if (
                        entity_type == "task" and
                        version['task']['id'] != entity['id']
                    ):
                        continue
                    # Get only components with allowed type
                    filetype = version['components'][0]['file_type']
                    if filetype[1:] in self.allowed_types:
                        versions.append(version)

        if len(versions) < 1:
            return {
                'success': False,
                'message': 'There are no Asset Versions to open.'
            }

        items = []
        base_label = "v{0} - {1} - {2}"
        default_component = self.config_data.get(
            'default_component', None
        )
        last_available = None
        select_value = None
        for version in versions:
            for component in version['components']:
                label = base_label.format(
                    str(version['version']).zfill(3),
                    version['asset']['type']['name'],
                    component['name']
                )

                try:
                    location = component[
                        'component_locations'
                    ][0]['location']
                    file_path = location.get_filesystem_path(component)
                except Exception:
                    file_path = component[
                        'component_locations'
                    ][0]['resource_identifier']

                if os.path.isdir(os.path.dirname(file_path)):
                    last_available = file_path
                    if component['name'] == default_component:
                        select_value = file_path
                    items.append(
                        {'label': label, 'value': file_path}
                    )

        if len(items) == 0:
            return {
                'success': False,
                'message': (
                    'There are no Asset Versions with accessible path.'
                )
            }

        item = {
            'label': 'Items to view',
            'type': 'enumerator',
            'name': 'path',
            'data': sorted(
                items,
                key=operator.itemgetter('label'),
                reverse=True
            )
        }
        if select_value is not None:
            item['value'] = select_value
        else:
            item['value'] = last_available

        return {'items': [item]}

    def launch(self, session, entities, event):
        """Callback method for RV action."""
        # Launching application
        if "values" not in event["data"]:
            return
        filename = event['data']['values']['path']

        fps = entities[0].get('custom_attributes', {}).get('fps', None)

        cmd = []
        # change frame number to padding string for RV to play sequence
        try:
            frame = re.findall(r'(\d+).', filename)[-1]
        except KeyError:
            # we didn't detected frame number
            pass
        else:
            padding = '#' * len(frame)
            pos = filename.rfind(frame)
            filename = filename[:pos] + padding + filename[
                filename.rfind('.'):]

        # RV path
        cmd.append(os.path.normpath(self.rv_path))
        if fps is not None:
            cmd.append("-fps {}".format(int(fps)))
        cmd.append(os.path.normpath(filename))
        log.info('Running rv: {}'.format(' '.join(cmd)))
        try:
            # Run RV with these commands
            subprocess.Popen(' '.join(cmd), shell=True)
        except Exception as e:
            return {
                'success': False,
                'message': 'File "{}" was not found.'.format(
                    e
                )
            }

        return True


def register(session):
    """Register hooks."""
    if not isinstance(session, ftrack_api.session.Session):
        return

    RVAction(session).register()


def main(arguments=None):
    '''Set up logging and register action.'''
    if arguments is None:
        arguments = []

    import argparse
    parser = argparse.ArgumentParser()
    # Allow setting of logging level from arguments.
    loggingLevels = {}
    for level in (
        logging.NOTSET, logging.DEBUG, logging.INFO, logging.WARNING,
        logging.ERROR, logging.CRITICAL
    ):
        loggingLevels[logging.getLevelName(level).lower()] = level

    parser.add_argument(
        '-v', '--verbosity',
        help='Set the logging output verbosity.',
        choices=loggingLevels.keys(),
        default='info'
    )
    namespace = parser.parse_args(arguments)

    # Set up basic logging
    logging.basicConfig(level=loggingLevels[namespace.verbosity])

    session = ftrack_api.Session()
    register(session)

    # Wait for events
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))

"""
Usage: RV movie and image sequence viewer

  One File:                   rv foo.jpg
  This Directory:             rv .
  Other Directory:            rv /path/to/dir
  Image Sequence w/Audio:     rv [ in.#.tif in.wav ]
  Stereo w/Audio:             rv [ left.#.tif right.#.tif in.wav ]
  Stereo Movies:              rv [ left.mov right.mov ]
  Stereo Movie (from rvio):   rv stereo.mov
  Cuts Sequenced:             rv cut1.mov cut2.#.exr cut3.mov
  Stereo Cuts Sequenced:      rv [ l1.mov r1.mov ] [ l2.mov r2.mov ]
  Forced Anamorphic:          rv [ -pa 2.0 fullaperture.#.dpx ]
  Compare:                    rv -wipe a.exr b.exr
  Difference:                 rv -diff a.exr b.exr
  Slap Comp Over:             rv -over a.exr b.exr
  Tile Images:                rv -tile *.jpg
  Cache + Play Movie:         rv -l -play foo.mov
  Cache Images to Examine:    rv -c big.#.exr
  Fullscreen on 2nd monitor:  rv -fullscreen -screen 1
  Select Source View:         rv [ in.exr -select view right ]
  Select Source Layer:        rv [ in.exr -select layer light1.diffuse ]
                              (single-view source)
  Select Source Layer:        rv [ in.exr -select layer left,light1.diffuse ]
                              (multi-view source)
  Select Source Channel:      rv [ in.exr -select channel R ]
                              (single-view, single-layer source)
  Select Source Channel:      rv [ in.exr -select channel left,Diffuse,R ]
                              (multi-view, multi-layer source)

Image Sequence Numbering

  Frames 1 to 100 no padding:     image.1-100@.jpg
  Frames 1 to 100 padding 4:      image.1-100#.jpg -or- image.1-100@@@@.jpg
  Frames 1 to 100 padding 5:      image.1-100@@@@@.jpg
  Frames -100 to -200 padding 4:  image.-100--200#jpg
  printf style padding 4:         image.%04d.jpg
  printf style w/range:           image.%04d.jpg 1-100
  printf no padding w/range:      image.%d.jpg 1-100
  Complicated no pad 1 to 100:    image_887f1-100@_982.tif
  Stereo pair (left,right):       image.#.%V.tif
  Stereo pair (L,R):              image.#.%v.tif
  All Frames, padding 4:          image.#.jpg
  All Frames in Sequence:         image.*.jpg
  All Frames in Directory:        /path/to/directory
  All Frames in current dir:      .

Per-source arguments (inside [ and ] restricts to that source only)

-pa %f                  Per-source pixel aspect ratio
-ro %d                  Per-source range offset
-rs %d                  Per-source range start
-fps %f                 Per-source or global fps
-ao %f                  Per-source audio offset in seconds
-so %f                  Per-source stereo relative eye offset
-rso %f                 Per-source stereo right eye offset
-volume %f              Per-source or global audio volume (default=1)
-fcdl %S                Per-source file CDL
-lcdl %S                Per-source look CDL
-flut %S                Per-source file LUT
-llut %S                Per-source look LUT
-pclut %S               Per-source pre-cache software LUT
-cmap %S                Per-source channel mapping
                        (channel names, separated by ',')
-select %S %S           Per-source view/layer/channel selection
-crop %d %d %d %d       Per-source crop (xmin, ymin, xmax, ymax)
-uncrop %d %d %d %d     Per-source uncrop (width, height, xoffset, yoffset)
-in %d                  Per-source cut-in frame
-out %d                 Per-source cut-out frame
-noMovieAudio           Disable source movie's baked-in audio
-inparams ...           Source specific input parameters

 ...                    Input sequence patterns, images, movies, or directories
-c                      Use region frame cache
-l                      Use look-ahead cache
-nc                     Use no caching
-s %f                   Image scale reduction
-ns                     Nuke style sequence notation
                        (deprecated and ignored -- no longer needed)
-noRanges               No separate frame ranges
                        (i.e. 1-10 will be considered a file)
-sessionType %S         Session type (sequence, stack) (deprecated, use -view)
-stereo %S              Stereo mode
                        (hardware, checker, scanline, anaglyph, lumanaglyph,
                        left, right, pair, mirror, hsqueezed, vsqueezed)
-stereoSwap %d          Swap left and right eyes stereo display
                        (0 == no, 1 == yes, default=0)
-vsync %d               Video Sync (1 = on, 0 = off, default = 1)
-comp %S                Composite mode
                        (over, add, difference, replace, topmost)
-layout %S              Layout mode (packed, row, column, manual)
-over                   Same as -comp over -view defaultStack
-diff                   Same as -comp difference -view defaultStack
-replace                Same as -comp replace -view defaultStack
-topmost                Same as -comp topmost -view defaultStack
-layer                  Same as -comp topmost -view defaultStack, with strict
                        frame ranges
-tile                   Same as -layout packed -view defaultLayout
-wipe                   Same as -over with wipes enabled
-view %S                Start with a particular view
-noSequence             Don't contract files into sequences
-inferSequence          Infer sequences from one file
-autoRetime %d          Automatically retime conflicting media fps in
                        sequences and stacks (1 = on, 0 = off, default = 1)
-rthreads %d            Number of reader threads (default=1)
-fullscreen             Start in fullscreen mode
-present                Start in presentation mode (using presentation device)
-presentAudio %d        Use presentation audio device in presentation mode
                        (1 = on, 0 = off)
-presentDevice %S       Presentation mode device
-presentVideoFormat %S  Presentation mode override video format
                        (device specific)
-presentDataFormat %S   Presentation mode override data format
                        (device specific)
-screen %d              Start on screen (0, 1, 2, ...)
-noBorders              No window manager decorations
-geometry %d %d [%d %d] Start geometry X, Y, W, H
-fitMedia               Fit the window to the first media shown
-init %S                Override init script
-nofloat                Turn off floating point by default
-maxbits %d             Maximum default bit depth (default=32)
-gamma %f               Set display gamma (default=1)
-sRGB                   Display using linear -> sRGB conversion
-rec709                 Display using linear -> Rec 709 conversion
-dlut %S                Apply display LUT
-brightness %f          Set display relative brightness in stops (default=0)
-resampleMethod %S      Resampling method
                        (area, linear, cubic, nearest, default=area)
-eval %S                Evaluate Mu expression at every session start
-pyeval %S              Evaluate Python expression at every session start
-nomb                   Hide menu bar on start up
-play                   Play on startup
-playMode %d            Playback mode (0=Context dependent, 1=Play all frames,
                        2=Realtime, default=0)
-loopMode %d            Playback loop mode
                        (0=Loop, 1=Play Once, 2=Ping-Pong, default=0)
-cli                    Mu command line interface
-vram %f                VRAM usage limit in Mb, default = 64.000000
-cram %f                Max region cache RAM usage in Gb,
                        (6.4Gb available, default 1Gb)
-lram %f                Max look-ahead cache RAM usage in Gb,
                        (6.4Gb available, default 0.2Gb)
-noPBO                  Prevent use of GL PBOs for pixel transfer
-prefetch               Prefetch images for rendering
-useAppleClientStorage  Use APPLE_client_storage extension
-useThreadedUpload      Use threading for texture uploading/downloading
                        if possible
-bwait %f               Max buffer wait time in cached seconds, default 5.0
-lookback %f            Percentage of the lookahead cache reserved for
                        frames behind the playhead, default 25
-yuv                    Assume YUV hardware conversion
-noaudio                Turn off audio
-audiofs %d             Use fixed audio frame size
                        (results are hardware dependant ... try 512)
-audioCachePacket %d    Audio cache packet size in samples (default=2048)
-audioMinCache %f       Audio cache min size in seconds (default=0.300000)
-audioMaxCache %f       Audio cache max size in seconds (default=0.600000)
-audioModule %S         Use specific audio module
-audioDevice %S         Use specific audio device
-audioRate %f           Use specific output audio rate (default=ask hardware)
-audioPrecision %d      Use specific output audio precision (default=16)
-audioNice %d           Close audio device when not playing
                        (may cause problems on some hardware) default=0
-audioNoLock %d         Do not use hardware audio/video syncronization
                        (use software instead, default=0)
-audioPreRoll %d        Preroll audio on device open (Linux only; default=0)
-audioGlobalOffset %f   Global audio offset in seconds
-audioDeviceLatency %f  Audio device latency compensation in milliseconds
-bg %S                  Background pattern (default=black, white, grey18,
                        grey50, checker, crosshatch)
-formats                Show all supported image and movie formats
-apple                  Use Quicktime and NSImage libraries (on OS X)
-cinalt                 Use alternate Cineon/DPX readers
-exrcpus %d             EXR thread count (default=0)
-exrRGBA                EXR Always read as RGBA (default=false)
-exrInherit             EXR guess channel inheritance (default=false)
-exrNoOneChannel        EXR never use one channel planar images (default=false)
-exrIOMethod %d [%d]    EXR I/O Method (0=standard, 1=buffered, 2=unbuffered,
                        3=MemoryMap, 4=AsyncBuffered, 5=AsyncUnbuffered,
                        default=1) and optional chunk size (default=61440)
-exrReadWindowIsDisplayWindow
                        EXR read window is display window (default=false)
-exrReadWindow %d       EXR Read Window Method (0=Data, 1=Display,
                        2=Union, 3=Data inside Display, default=3)
-jpegRGBA               Make JPEG four channel RGBA on read
                        (default=no, use RGB or YUV)
-jpegIOMethod %d [%d]   JPEG I/O Method (0=standard, 1=buffered,
                        2=unbuffered, 3=MemoryMap, 4=AsyncBuffered,
                        5=AsyncUnbuffered, default=1) and optional
                        chunk size (default=61440)
-cinpixel %S            Cineon pixel storage (default=RGB8_PLANAR)
-cinchroma              Use Cineon chromaticity values
                        (for default reader only)
-cinIOMethod %d [%d]    Cineon I/O Method (0=standard, 1=buffered,
                        2=unbuffered, 3=MemoryMap, 4=AsyncBuffered,
                        5=AsyncUnbuffered, default=1) and optional
                        chunk size (default=61440)
-dpxpixel %S            DPX pixel storage (default=RGB8_PLANAR)
-dpxchroma              Use DPX chromaticity values (for default reader only)
-dpxIOMethod %d [%d]    DPX I/O Method (0=standard, 1=buffered, 2=unbuffered,
                        3=MemoryMap, 4=AsyncBuffered, 5=AsyncUnbuffered,
                        default=1) and optional chunk size (default=61440)
-tgaIOMethod %d [%d]    TARGA I/O Method (0=standard, 1=buffered,
                        2=unbuffered, 3=MemoryMap, 4=AsyncBuffered,
                        5=AsyncUnbuffered, default=1)
                        and optional chunk size (default=61440)
-tiffIOMethod %d [%d]   TIFF I/O Method (0=standard, 1=buffered,
                        2=unbuffered, 3=MemoryMap, 4=AsyncBuffered,
                        5=AsyncUnbuffered, default=1) and optional
                        chunk size (default=61440)
-lic %S                 Use specific license file
-noPrefs                Ignore preferences
-resetPrefs             Reset preferences to default values
-qtcss %S               Use QT style sheet for UI
-qtstyle %S             Use QT style
-qtdesktop %d           QT desktop aware, default=1 (on)
-xl                     Aggressively absorb screen space for large media
-mouse %d               Force tablet/stylus events to be treated as a
                        mouse events, default=0 (off)
-network                Start networking
-networkPort %d         Port for networking
-networkHost %S         Alternate host/address for incoming connections
-networkTag %S          Tag to mark automatically saved port file
-networkConnect %S [%d] Start networking and connect to host at port
-networkPerm %d         Default network connection permission
                        (0=Ask, 1=Allow, 2=Deny, default=0)
-reuse %d               Try to re-use the current session for
                        incoming URLs (1 = reuse session,
                        0 = new session, default = 1)
-nopackages             Don't load any packages at startup (for debugging)
-encodeURL              Encode the command line as
                        an rvlink URL, print, and exit
-bakeURL                Fully bake the command line as an
                        rvlink URL, print, and exit
-sendEvent ...          Send external events e.g. -sendEvent 'name' 'content'
-flags ...              Arbitrary flags (flag, or 'name=value')
                        for use in Mu code
-debug ...              Debug category
-version                Show RV version number
-strictlicense          Exit rather than consume an rv license if no rvsolo
                        licenses are available
-prefsPath %S           Alternate path to preferences directory
-sleep %d               Sleep (in seconds) before starting to
                        allow attaching debugger
"""
