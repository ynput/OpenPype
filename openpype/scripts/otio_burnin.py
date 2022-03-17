import os
import sys
import re
import subprocess
import platform
import json
import opentimelineio_contrib.adapters.ffmpeg_burnins as ffmpeg_burnins

from openpype.lib import (
    get_ffmpeg_tool_path,
    get_ffmpeg_codec_args,
    get_ffmpeg_format_args,
    convert_ffprobe_fps_value,
)


ffmpeg_path = get_ffmpeg_tool_path("ffmpeg")
ffprobe_path = get_ffmpeg_tool_path("ffprobe")


FFMPEG = (
    '"{}"%(input_args)s -i "%(input)s" %(filters)s %(args)s%(output)s'
).format(ffmpeg_path)

FFPROBE = (
    '"{}" -v quiet -print_format json -show_format -show_streams "%(source)s"'
).format(ffprobe_path)

DRAWTEXT = (
    "drawtext=fontfile='%(font)s':text=\\'%(text)s\\':"
    "x=%(x)s:y=%(y)s:fontcolor=%(color)s@%(opacity).1f:fontsize=%(size)d"
)
TIMECODE = (
    "drawtext=timecode=\\'%(timecode)s\\':text=\\'%(text)s\\'"
    ":timecode_rate=%(fps).2f:x=%(x)s:y=%(y)s:fontcolor="
    "%(color)s@%(opacity).1f:fontsize=%(size)d:fontfile='%(font)s'"
)

MISSING_KEY_VALUE = "N/A"
CURRENT_FRAME_KEY = "{current_frame}"
CURRENT_FRAME_SPLITTER = "_-_CURRENT_FRAME_-_"
TIMECODE_KEY = "{timecode}"
SOURCE_TIMECODE_KEY = "{source_timecode}"


def _get_ffprobe_data(source):
    """Reimplemented from otio burnins to be able use full path to ffprobe
    :param str source: source media file
    :rtype: [{}, ...]
    """
    command = FFPROBE % {'source': source}
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    out = proc.communicate()[0]
    if proc.returncode != 0:
        raise RuntimeError("Failed to run: %s" % command)
    return json.loads(out)


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
    General can be overridden when adding burnin

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

    def __init__(
        self, source, ffprobe_data=None, options_init=None, first_frame=None
    ):
        if not ffprobe_data:
            ffprobe_data = _get_ffprobe_data(source)

        self.ffprobe_data = ffprobe_data
        self.first_frame = first_frame
        self.input_args = []

        super().__init__(source, ffprobe_data["streams"])

        if options_init:
            self.options_init.update(options_init)

    def add_text(
        self, text, align, frame_start=None, frame_end=None, options=None
    ):
        """
        Adding static text to a filter.

        :param str text: text to apply to the drawtext
        :param enum align: alignment, must use provided enum flags
        :param int frame_start: starting frame for burnins current frame
        :param dict options: recommended to use TextOptions
        """
        if not options:
            options = ffmpeg_burnins.TextOptions(**self.options_init)

        options = options.copy()
        if frame_start is not None:
            options["frame_offset"] = frame_start

        # `frame_end` is only for meassurements of text position
        if frame_end is not None:
            options["frame_end"] = frame_end

        self._add_burnin(text, align, options, DRAWTEXT)

    def add_timecode(
        self, align, frame_start=None, frame_end=None, frame_start_tc=None,
        text=None, options=None
    ):
        """
        Convenience method to create the frame number expression.

        :param enum align: alignment, must use provided enum flags
        :param int frame_start:  starting frame for burnins current frame
        :param int frame_start_tc:  starting frame for burnins timecode
        :param str text: text that will be before timecode
        :param dict options: recommended to use TimeCodeOptions
        """
        if not options:
            options = ffmpeg_burnins.TimeCodeOptions(**self.options_init)

        options = options.copy()
        if frame_start is not None:
            options["frame_offset"] = frame_start

        # `frame_end` is only for meassurements of text position
        if frame_end is not None:
            options["frame_end"] = frame_end

        if not frame_start_tc:
            frame_start_tc = options["frame_offset"]

        if not text:
            text = ""

        if not options.get("fps"):
            options["fps"] = self.frame_rate

        if isinstance(frame_start_tc, str):
            options["timecode"] = frame_start_tc
        else:
            options["timecode"] = ffmpeg_burnins._frames_to_timecode(
                frame_start_tc,
                self.frame_rate
            )

        self._add_burnin(text, align, options, TIMECODE)

    def _add_burnin(self, text, align, options, draw):
        """
        Generic method for building the filter flags.
        :param str text: text to apply to the drawtext
        :param enum align: alignment, must use provided enum flags
        :param dict options:
        """

        final_text = text
        text_for_size = text
        if CURRENT_FRAME_SPLITTER in text:
            frame_start = options["frame_offset"]
            frame_end = options.get("frame_end", frame_start)
            if frame_start is None:
                replacement_final = replacement_size = str(MISSING_KEY_VALUE)
            else:
                replacement_final = "%{eif:n+" + str(frame_start) + ":d:" + \
                                    str(len(str(frame_end))) + "}"
                replacement_size = str(frame_end)

            final_text = final_text.replace(
                CURRENT_FRAME_SPLITTER, replacement_final
            )
            text_for_size = text_for_size.replace(
                CURRENT_FRAME_SPLITTER, replacement_size
            )

        resolution = self.resolution
        data = {
            'text': (
                final_text
                .replace(",", r"\,")
                .replace(':', r'\:')
            ),
            'color': options['font_color'],
            'size': options['font_size']
        }
        timecode_text = options.get("timecode") or ""
        text_for_size += timecode_text

        font_path = options.get("font")
        if not font_path or not os.path.exists(font_path):
            font_path = ffmpeg_burnins.FONT

        options["font"] = font_path

        data.update(options)
        data.update(
            ffmpeg_burnins._drawtext(align, resolution, text_for_size, options)
        )

        arg_font_path = font_path
        if platform.system().lower() == "windows":
            arg_font_path = (
                arg_font_path
                .replace(os.sep, r'\\' + os.sep)
                .replace(':', r'\:')
            )
        data["font"] = arg_font_path

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
        output = '"{}"'.format(output or '')
        if overwrite:
            output = '-y {}'.format(output)

        filters = ''
        if self.filter_string:
            filters = '-vf "{}"'.format(self.filter_string)

        if self.first_frame is not None:
            start_number_arg = "-start_number {}".format(self.first_frame)
            self.input_args.append(start_number_arg)
            if "start_number" not in args:
                if not args:
                    args = start_number_arg
                else:
                    args = " ".join((start_number_arg, args))

        input_args = ""
        if self.input_args:
            input_args = " {}".format(" ".join(self.input_args))

        return (FFMPEG % {
            'input_args': input_args,
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

        command = self.command(
            output=output,
            args=args,
            overwrite=overwrite
        )
        print("Launching command: {}".format(command))

        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )

        _stdout, _stderr = proc.communicate()
        if _stdout:
            for line in _stdout.split(b"\r\n"):
                print(line.decode("utf-8"))

        # This will probably never happen as ffmpeg use stdout
        if _stderr:
            for line in _stderr.split(b"\r\n"):
                print(line.decode("utf-8"))

        if proc.returncode != 0:
            raise RuntimeError(
                "Failed to render '{}': {}'".format(output, command)
            )
        if is_sequence:
            output = output % kwargs.get("duration")

        if not os.path.exists(output):
            raise RuntimeError(
                "Failed to generate this f*cking file '%s'" % output
            )


def example(input_path, output_path):
    options_init = {
        'opacity': 1,
        'x_offset': 10,
        'y_offset': 10,
        'bg_padding': 10,
        'bg_opacity': 0.5,
        'font_size': 52
    }
    # Options init sets burnin look
    burnin = ModifiedBurnins(input_path, options_init=options_init)
    # Static text
    burnin.add_text('My Text', ModifiedBurnins.TOP_CENTERED)
    # Datetime
    burnin.add_text('%d-%m-%y', ModifiedBurnins.TOP_RIGHT)
    # Start render (overwrite output file if exist)
    burnin.render(output_path, overwrite=True)


def burnins_from_data(
    input_path, output_path, data,
    codec_data=None, options=None, burnin_values=None, overwrite=True,
    full_input_path=None, first_frame=None, source_ffmpeg_cmd=None
):
    """This method adds burnins to video/image file based on presets setting.

    Extension of output MUST be same as input. (mov -> mov, avi -> avi,...)

    Args:
        input_path (str): Full path to input file where burnins should be add.
        output_path (str): Full path to output file where output will be
            rendered.
        data (dict): Data required for burnin settings (more info below).
        codec_data (list): All codec related arguments in list.
        options (dict): Options for burnins.
        burnin_values (dict): Contain positioned values.
        overwrite (bool): Output will be overwritten if already exists,
            True by default.

    Presets must be set separately. Should be dict with 2 keys:
    - "options" - sets look of burnins - colors, opacity,...(more info: ModifiedBurnins doc)
                - *OPTIONAL* default values are used when not included
    - "burnins" - contains dictionary with burnins settings
                - *OPTIONAL* burnins won't be added (easier is not to use this)
        - each key of "burnins" represents Alignment, there are 6 possibilities:
            TOP_LEFT        TOP_CENTERED        TOP_RIGHT
            BOTTOM_LEFT     BOTTOM_CENTERED     BOTTOM_RIGHT
        - value must be string with text you want to burn-in
        - text may contain specific formatting keys (exmplained below)

    Requirement of *data* keys is based on presets.
    - "frame_start" - is required when "timecode" or "current_frame" ins keys
    - "frame_start_tc" - when "timecode" should start with different frame
    - *keys for static text*

    EXAMPLE:
    preset = {
        "options": {*OPTIONS FOR LOOK*},
        "burnins": {
            "TOP_LEFT": "static_text",
            "TOP_RIGHT": "{shot}",
            "BOTTOM_LEFT": "TC: {timecode}",
            "BOTTOM_RIGHT": "{frame_start}{current_frame}"
        }
    }

    For this preset we'll need at least this data:
    data = {
        "frame_start": 1001,
        "shot": "sh0010"
    }

    When Timecode should start from 1 then data need:
    data = {
        "frame_start": 1001,
        "frame_start_tc": 1,
        "shot": "sh0010"
    }
    """
    ffprobe_data = None
    if full_input_path:
        ffprobe_data = _get_ffprobe_data(full_input_path)

    burnin = ModifiedBurnins(input_path, ffprobe_data, options, first_frame)

    frame_start = data.get("frame_start")
    frame_end = data.get("frame_end")
    frame_start_tc = data.get('frame_start_tc', frame_start)

    stream = burnin._streams[0]
    if "resolution_width" not in data:
        data["resolution_width"] = stream.get("width", MISSING_KEY_VALUE)

    if "resolution_height" not in data:
        data["resolution_height"] = stream.get("height", MISSING_KEY_VALUE)

    if "fps" not in data:
        data["fps"] = convert_ffprobe_fps_value(
            stream.get("r_frame_rate", "0/0")
        )

    # Check frame start and add expression if is available
    if frame_start is not None:
        data[CURRENT_FRAME_KEY[1:-1]] = CURRENT_FRAME_SPLITTER

    if frame_start_tc is not None:
        data[TIMECODE_KEY[1:-1]] = TIMECODE_KEY

    source_timecode = stream.get("timecode")
    if source_timecode is None:
        source_timecode = stream.get("tags", {}).get("timecode")

    # Use "format" key from ffprobe data
    #   - this is used e.g. in mxf extension
    if source_timecode is None:
        input_format = burnin.ffprobe_data.get("format") or {}
        source_timecode = input_format.get("timecode")
        if source_timecode is None:
            source_timecode = input_format.get("tags", {}).get("timecode")

    if source_timecode is not None:
        data[SOURCE_TIMECODE_KEY[1:-1]] = SOURCE_TIMECODE_KEY

    for align_text, value in burnin_values.items():
        if not value:
            continue

        if isinstance(value, (dict, list, tuple)):
            raise TypeError((
                "Expected string or number type."
                " Got: {} - \"{}\""
                " (Make sure you have new burnin presets)."
            ).format(str(type(value)), str(value)))

        align = None
        align_text = align_text.strip().lower()
        if align_text == "top_left":
            align = ModifiedBurnins.TOP_LEFT
        elif align_text == "top_centered":
            align = ModifiedBurnins.TOP_CENTERED
        elif align_text == "top_right":
            align = ModifiedBurnins.TOP_RIGHT
        elif align_text == "bottom_left":
            align = ModifiedBurnins.BOTTOM_LEFT
        elif align_text == "bottom_centered":
            align = ModifiedBurnins.BOTTOM_CENTERED
        elif align_text == "bottom_right":
            align = ModifiedBurnins.BOTTOM_RIGHT

        has_timecode = TIMECODE_KEY in value
        # Replace with missing key value if frame_start_tc is not set
        if frame_start_tc is None and has_timecode:
            has_timecode = False
            print(
                "`frame_start` and `frame_start_tc`"
                " are not set in entered data."
            )
            value = value.replace(TIMECODE_KEY, MISSING_KEY_VALUE)

        has_source_timecode = SOURCE_TIMECODE_KEY in value
        if source_timecode is None and has_source_timecode:
            has_source_timecode = False
            print("Source does not have set timecode value.")
            value = value.replace(SOURCE_TIMECODE_KEY, MISSING_KEY_VALUE)

        key_pattern = re.compile(r"(\{.*?[^{0]*\})")

        missing_keys = []
        for group in key_pattern.findall(value):
            try:
                group.format(**data)
            except (TypeError, KeyError):
                missing_keys.append(group)

        missing_keys = list(set(missing_keys))
        for key in missing_keys:
            value = value.replace(key, MISSING_KEY_VALUE)

        # Handle timecode differently
        if has_source_timecode:
            args = [align, frame_start, frame_end, source_timecode]
            if not value.startswith(SOURCE_TIMECODE_KEY):
                value_items = value.split(SOURCE_TIMECODE_KEY)
                text = value_items[0].format(**data)
                args.append(text)

            burnin.add_timecode(*args)
            continue

        if has_timecode:
            args = [align, frame_start, frame_end, frame_start_tc]
            if not value.startswith(TIMECODE_KEY):
                value_items = value.split(TIMECODE_KEY)
                text = value_items[0].format(**data)
                args.append(text)

            burnin.add_timecode(*args)
            continue

        text = value.format(**data)
        burnin.add_text(text, align, frame_start, frame_end)

    ffmpeg_args = []
    if codec_data:
        # Use codec definition from method arguments
        ffmpeg_args = codec_data
        ffmpeg_args.append("-g 1")

    else:
        ffmpeg_args.extend(
            get_ffmpeg_format_args(burnin.ffprobe_data, source_ffmpeg_cmd)
        )
        ffmpeg_args.extend(
            get_ffmpeg_codec_args(burnin.ffprobe_data, source_ffmpeg_cmd)
        )
        # Use arguments from source if are available source arguments
        if source_ffmpeg_cmd:
            copy_args = (
                "-metadata",
            )
            args = source_ffmpeg_cmd.split(" ")
            for idx, arg in enumerate(args):
                if arg in copy_args:
                    ffmpeg_args.extend([arg, args[idx + 1]])

    # Use group one (same as `-intra` argument, which is deprecated)
    ffmpeg_args_str = " ".join(ffmpeg_args)
    burnin.render(
        output_path, args=ffmpeg_args_str, overwrite=overwrite, **data
    )


if __name__ == "__main__":
    print("* Burnin script started")
    in_data_json_path = sys.argv[-1]
    with open(in_data_json_path, "r") as file_stream:
        in_data = json.load(file_stream)

    burnins_from_data(
        in_data["input"],
        in_data["output"],
        in_data["burnin_data"],
        codec_data=in_data.get("codec"),
        options=in_data.get("options"),
        burnin_values=in_data.get("values"),
        full_input_path=in_data.get("full_input_path"),
        first_frame=in_data.get("first_frame"),
        source_ffmpeg_cmd=in_data.get("ffmpeg_cmd")
    )
    print("* Burnin script has finished")
