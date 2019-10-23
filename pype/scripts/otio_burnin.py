import os
import datetime
import opentimelineio_contrib.adapters.ffmpeg_burnins as ffmpeg_burnins
from pypeapp.lib import config
from pype import api as pype
# FFmpeg in PATH is required


log = pype.Logger().get_logger("BurninWrapper", "burninwrap")


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

    def add_frame_numbers(self, align, options=None, start_frame=None):
        """
        Convenience method to create the frame number expression.

        :param enum align: alignment, must use provided enum flags
        :param dict options: recommended to use FrameNumberOptions
        """
        if not options:
            options = ffmpeg_burnins.FrameNumberOptions(**self.options_init)
        if start_frame:
            options['frame_offset'] = start_frame

        options['expression'] = r'%%{eif\:n+%d\:d}' % options['frame_offset']
        text = str(int(self.end_frame + options['frame_offset']))
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

        return (ffmpeg_burnins.FFMPEG % {
            'input': self.source,
            'output': output,
            'args': '%s ' % args if args else '',
            'filters': filters
        }).strip()


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


def burnins_from_data(input_path, output_path, data, overwrite=True):
    '''
    This method adds burnins to video/image file based on presets setting.
    Extension of output MUST be same as input. (mov -> mov, avi -> avi,...)

    :param input_path: full path to input file where burnins should be add
    :type input_path: str
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

    start_frame = data.get("start_frame")
    start_frame_tc = data.get('start_frame_tc', start_frame)
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
            start_frame is None
        ):
            log.error(
                'start_frame is not set in entered data!'
                'Burnins are not created!'
            )
            return

        if bi_func == 'frame_numbers':
            burnin.add_frame_numbers(align, start_frame=start_frame)
        elif bi_func == 'timecode':
            burnin.add_timecode(align, start_frame=start_frame_tc)
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

    burnin.render(output_path, overwrite=overwrite)


if __name__ == '__main__':
    import sys
    import json
    data = json.loads(sys.argv[-1])
    burnins_from_data(data['input'], data['output'], data['burnin_data'])
