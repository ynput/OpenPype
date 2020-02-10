import os
import datetime
import subprocess
import json
import opentimelineio_contrib.adapters.ffmpeg_burnins as ffmpeg_burnins
from pypeapp.lib import config
from pype import api as pype
from subprocess import Popen, PIPE
# FFmpeg in PATH is required


log = pype.Logger().get_logger("BurninWrapper", "burninwrap")


ffmpeg_path = os.environ.get("FFMPEG_PATH")
if ffmpeg_path and os.path.exists(ffmpeg_path):
    # add separator "/" or "\" to be prepared for next part
    ffmpeg_path += os.path.sep
else:
    ffmpeg_path = ""

FFMPEG = (
    '{} -loglevel panic -i %(input)s %(filters)s %(args)s%(output)s'
).format(os.path.normpath(ffmpeg_path + "ffmpeg"))

FFPROBE = (
    '{} -v quiet -print_format json -show_format -show_streams %(source)s'
).format(os.path.normpath(ffmpeg_path + "ffprobe"))


def _streams(source):
    """Reimplemented from otio burnins to be able use full path to ffprobe
    :param str source: source media file
    :rtype: [{}, ...]
    """
    command = FFPROBE % {'source': source}
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    out = proc.communicate()[0]
    if proc.returncode != 0:
        raise RuntimeError("Failed to run: %s" % command)
    return json.loads(out)['streams']


def get_fps(str_value):
    if str_value == "0/0":
        print("Source has \"r_frame_rate\" value set to \"0/0\".")
        return "Unknown"

    items = str_value.split("/")
    if len(items) == 1:
        fps = float(items[0])

    elif len(items) == 2:
        fps = float(items[0]) / float(items[1])

    # Check if fps is integer or float number
    if int(fps) == fps:
        fps = int(fps)

    return str(fps)


class ModifiedBurnins(ffmpeg_burnins.Burnins):
    '''
    This is modification of OTIO FFmpeg Burnin adapter.
    - requires FFmpeg in PATH

    Offers 6 positions for burnin text. Each can be set with:
    - static text
    - frames
    - timecode

    Options - dictionary which sets the final look.
    - Datatypes explanation:
    <color> string format must be supported by FFmpeg.
        Examples: "#000000", "0x000000", "black"
    <font> must be accesible by ffmpeg = name of registered Font in system or path to font file.
        Examples: "Arial", "C:/Windows/Fonts/arial.ttf"

    - Possible keys:
    "opacity" - Opacity of text - <float, Range:0-1>
    "bg_opacity" - Opacity of background (box around text) - <float, Range:0-1>
    "bg_color" - Background color - <color>
    "bg_padding" - Background padding in pixels - <int>
    "x_offset" - offsets burnin vertically by entered pixels from border - <int>
    "y_offset" - offsets burnin horizontally by entered pixels from border - <int>
    - x_offset & y_offset should be set at least to same value as bg_padding!!
    "font" - Font Family for text - <font>
    "font_size" - Font size in pixels - <int>
    "font_color" - Color of text - <color>
    "frame_offset" - Default start frame - <int>
        - required IF start frame is not set when using frames or timecode burnins

    On initializing class can be set General options through "options_init" arg.
    General can be overriden when adding burnin

    '''
    TOP_CENTERED = ffmpeg_burnins.TOP_CENTERED
    BOTTOM_CENTERED = ffmpeg_burnins.BOTTOM_CENTERED
    TOP_LEFT = ffmpeg_burnins.TOP_LEFT
    BOTTOM_LEFT = ffmpeg_burnins.BOTTOM_LEFT
    TOP_RIGHT = ffmpeg_burnins.TOP_RIGHT
    BOTTOM_RIGHT = ffmpeg_burnins.BOTTOM_RIGHT

    options_init = {
        'opacity': 1,
        'x_offset': 5,
        'y_offset': 5,
        'bg_padding': 5,
        'bg_opacity': 0.5,
        'font_size': 42
    }

    def __init__(self, source, streams=None, options_init=None):
        if not streams:
            streams = _streams(source)

        super().__init__(source, streams)

        if options_init:
            self.options_init.update(options_init)

    def add_text(self, text, align, options=None):
        """
        Adding static text to a filter.

        :param str text: text to apply to the drawtext
        :param enum align: alignment, must use provided enum flags
        :param dict options: recommended to use TextOptions
        """
        if not options:
            options = ffmpeg_burnins.TextOptions(**self.options_init)
        self._add_burnin(text, align, options, ffmpeg_burnins.DRAWTEXT)

    def add_datetime(self, date_format, align, options=None):
        """
        Adding date text to a filter. Using pythons datetime module.

        :param str date_format: format of date (e.g. `%d.%m.%Y`)
        :param enum align: alignment, must use provided enum flags
        :param dict options: recommended to use TextOptions
        """
        if not options:
            options = ffmpeg_burnins.TextOptions(**self.options_init)
        today = datetime.datetime.today()
        text = today.strftime(date_format)
        self._add_burnin(text, align, options, ffmpeg_burnins.DRAWTEXT)

    def add_frame_numbers(
        self, align, options=None, start_frame=None, text=None
    ):
        """
        Convenience method to create the frame number expression.

        :param enum align: alignment, must use provided enum flags
        :param dict options: recommended to use FrameNumberOptions
        """
        if not options:
            options = ffmpeg_burnins.FrameNumberOptions(**self.options_init)
        if start_frame:
            options['frame_offset'] = start_frame

        expr = r'%%{eif\:n+%d\:d}' % options['frame_offset']
        _text = str(int(self.end_frame + options['frame_offset']))
        if text and isinstance(text, str):
            text = r"{}".format(text)
            expr = text.replace("{current_frame}", expr)
            text = text.replace("{current_frame}", _text)

        options['expression'] = expr
        self._add_burnin(text, align, options, ffmpeg_burnins.DRAWTEXT)

    def add_timecode(self, align, options=None, start_frame=None):
        """
        Convenience method to create the frame number expression.

        :param enum align: alignment, must use provided enum flags
        :param dict options: recommended to use TimeCodeOptions
        """
        if not options:
            options = ffmpeg_burnins.TimeCodeOptions(**self.options_init)
        if start_frame:
            options['frame_offset'] = start_frame

        timecode = ffmpeg_burnins._frames_to_timecode(
            options['frame_offset'],
            self.frame_rate
        )
        options = options.copy()
        if not options.get('fps'):
            options['fps'] = self.frame_rate

        self._add_burnin(
            timecode.replace(':', r'\:'),
            align,
            options,
            ffmpeg_burnins.TIMECODE
        )

    def _add_burnin(self, text, align, options, draw):
        """
        Generic method for building the filter flags.
        :param str text: text to apply to the drawtext
        :param enum align: alignment, must use provided enum flags
        :param dict options:
        """
        resolution = self.resolution
        data = {
            'text': options.get('expression') or text,
            'color': options['font_color'],
            'size': options['font_size']
        }
        data.update(options)
        data.update(ffmpeg_burnins._drawtext(align, resolution, text, options))
        if 'font' in data and ffmpeg_burnins._is_windows():
            data['font'] = data['font'].replace(os.sep, r'\\' + os.sep)
            data['font'] = data['font'].replace(':', r'\:')
        self.filters['drawtext'].append(draw % data)

        if options.get('bg_color') is not None:
            box = ffmpeg_burnins.BOX % {
                'border': options['bg_padding'],
                'color': options['bg_color'],
                'opacity': options['bg_opacity']
            }
            self.filters['drawtext'][-1] += ':%s' % box

    def command(self, output=None, args=None, overwrite=False):
        """
        Generate the entire FFMPEG command.

        :param str output: output file
        :param str args: additional FFMPEG arguments
        :param bool overwrite: overwrite the output if it exists
        :returns: completed command
        :rtype: str
        """
        output = output or ''
        if overwrite:
            output = '-y {}'.format(output)

        filters = ''
        if self.filter_string:
            filters = '-vf "{}"'.format(self.filter_string)

        return (FFMPEG % {
            'input': self.source,
            'output': output,
            'args': '%s ' % args if args else '',
            'filters': filters
        }).strip()

    def render(self, output, args=None, overwrite=False, **kwargs):
        """
        Render the media to a specified destination.

        :param str output: output file
        :param str args: additional FFMPEG arguments
        :param bool overwrite: overwrite the output if it exists
        """
        if not overwrite and os.path.exists(output):
            raise RuntimeError("Destination '%s' exists, please "
                               "use overwrite" % output)

        is_sequence = "%" in output

        command = self.command(output=output,
                               args=args,
                               overwrite=overwrite)
        proc = Popen(command, shell=True)
        proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError("Failed to render '%s': %s'"
                               % (output, command))
        if is_sequence:
            output = output % kwargs.get("duration")
        if not os.path.exists(output):
            raise RuntimeError("Failed to generate this fucking file '%s'" % output)


def example(input_path, output_path):
    options_init = {
        'opacity': 1,
        'x_offset': 10,
        'y_offset': 10,
        'bg_padding': 10,
        'bg_opacity': 0.5,
        'font_size': 52
    }
    # First frame in burnin
    start_frame = 2000
    # Options init sets burnin look
    burnin = ModifiedBurnins(input_path, options_init=options_init)
    # Static text
    burnin.add_text('My Text', ModifiedBurnins.TOP_CENTERED)
    # Datetime
    burnin.add_text('%d-%m-%y', ModifiedBurnins.TOP_RIGHT)
    # Frame number
    burnin.add_frame_numbers(ModifiedBurnins.TOP_RIGHT, start_frame=start_frame)
    # Timecode
    burnin.add_timecode(ModifiedBurnins.TOP_LEFT, start_frame=start_frame)
    # Start render (overwrite output file if exist)
    burnin.render(output_path, overwrite=True)


def burnins_from_data(input_path, codec_data, output_path, data, overwrite=True):
    '''
    This method adds burnins to video/image file based on presets setting.
    Extension of output MUST be same as input. (mov -> mov, avi -> avi,...)

    :param input_path: full path to input file where burnins should be add
    :type input_path: str
    :param codec_data: all codec related arguments in list
    :param codec_data: list
    :param output_path: full path to output file where output will be rendered
    :type output_path: str
    :param data: data required for burnin settings (more info below)
    :type data: dict
    :param overwrite: output will be overriden if already exists, defaults to True
    :type overwrite: bool

    Presets must be set separately. Should be dict with 2 keys:
    - "options" - sets look of burnins - colors, opacity,...(more info: ModifiedBurnins doc)
                - *OPTIONAL* default values are used when not included
    - "burnins" - contains dictionary with burnins settings
                - *OPTIONAL* burnins won't be added (easier is not to use this)
        - each key of "burnins" represents Alignment, there are 6 possibilities:
            TOP_LEFT        TOP_CENTERED        TOP_RIGHT
            BOTTOM_LEFT     BOTTOM_CENTERED     BOTTOM_RIGHT
        - value for each key is dict which should contain "function" which says
            what kind of burnin is that:
            "text", "timecode" or "frame_numbers"
            - "text" key with content is also required when "text" function is used

    Requirement of *data* keys is based on presets.
    - "start_frame" - is required when "timecode" or "frame_numbers" function is used
    - "start_frame_tc" - when "timecode" should start with different frame
    - *keys for static text*

    EXAMPLE:
    preset = {
        "options": {*OPTIONS FOR LOOK*},
        "burnins": {
            "TOP_LEFT": {
                "function": "text",
                "text": "static_text"
            },
            "TOP_RIGHT": {
                "function": "text",
                "text": "{shot}"
            },
            "BOTTOM_LEFT": {
                "function": "timecode"
            },
            "BOTTOM_RIGHT": {
                "function": "frame_numbers"
            }
        }
    }

    For this preset we'll need at least this data:
    data = {
        "start_frame": 1001,
        "shot": "sh0010"
    }

    When Timecode should start from 1 then data need:
    data = {
        "start_frame": 1001,
        "start_frame_tc": 1,
        "shot": "sh0010"
    }
    '''
    presets = config.get_presets().get('tools', {}).get('burnins', {})
    options_init = presets.get('options')

    burnin = ModifiedBurnins(input_path, options_init=options_init)

    frame_start = data.get("frame_start")
    frame_start_tc = data.get('frame_start_tc', frame_start)

    stream = burnin._streams[0]
    if "resolution_width" not in data:
        data["resolution_width"] = stream.get("width", "Unknown")

    if "resolution_height" not in data:
        data["resolution_height"] = stream.get("height", "Unknown")

    if "fps" not in data:
        data["fps"] = get_fps(stream.get("r_frame_rate", "0/0"))

    for align_text, preset in presets.get('burnins', {}).items():
        align = None
        if align_text == 'TOP_LEFT':
            align = ModifiedBurnins.TOP_LEFT
        elif align_text == 'TOP_CENTERED':
            align = ModifiedBurnins.TOP_CENTERED
        elif align_text == 'TOP_RIGHT':
            align = ModifiedBurnins.TOP_RIGHT
        elif align_text == 'BOTTOM_LEFT':
            align = ModifiedBurnins.BOTTOM_LEFT
        elif align_text == 'BOTTOM_CENTERED':
            align = ModifiedBurnins.BOTTOM_CENTERED
        elif align_text == 'BOTTOM_RIGHT':
            align = ModifiedBurnins.BOTTOM_RIGHT

        bi_func = preset.get('function')
        if not bi_func:
            log.error(
                'Missing function for burnin!'
                'Burnins are not created!'
            )
            return

        if (
            bi_func in ['frame_numbers', 'timecode'] and
            frame_start is None
        ):
            log.error(
                'start_frame is not set in entered data!'
                'Burnins are not created!'
            )
            return

        if bi_func == 'frame_numbers':
            current_frame_identifier = "{current_frame}"
            text = preset.get('text') or current_frame_identifier

            if current_frame_identifier not in text:
                log.warning((
                    'Text for Frame numbers don\'t have '
                    '`{current_frame}` key in text!'
                ))

            text_items = []
            split_items = text.split(current_frame_identifier)
            for item in split_items:
                text_items.append(item.format(**data))

            text = "{current_frame}".join(text_items)

            burnin.add_frame_numbers(align, start_frame=frame_start, text=text)

        elif bi_func == 'timecode':
            burnin.add_timecode(align, start_frame=frame_start_tc)

        elif bi_func == 'text':
            if not preset.get('text'):
                log.error('Text is not set for text function burnin!')
                return
            text = preset['text'].format(**data)
            burnin.add_text(text, align)

        elif bi_func == "datetime":
            date_format = preset["format"]
            burnin.add_datetime(date_format, align)

        else:
            log.error(
                'Unknown function for burnins {}'.format(bi_func)
            )
            return

    codec_args = ''
    if codec_data is not []:
        codec_args = " ".join(codec_data)

    burnin.render(output_path, args=codec_args, overwrite=overwrite, **data)


if __name__ == '__main__':
    import sys
    import json
    data = json.loads(sys.argv[-1])
    burnins_from_data(
        data['input'],
        data['codec'],
        data['output'],
        data['burnin_data']
    )
