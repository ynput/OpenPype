# -*- coding: utf-8 -*-
"""Package helping with colorizing and formatting terminal output."""
# ::
#   //.  ...   ..      ///.     //.
#  ///\\\ \\\   \\    ///\\\   ///
# ///  \\  \\\   \\  ///  \\  /// //
# \\\  //   \\\  //  \\\  //  \\\//  ./
#  \\\//     \\\//    \\\//    \\\' //
#   \\\         \\\    \\\      \\\//
#    '''         '''    '''      '''
#   ..---===[[ PyP3 Setup ]]===---...
#
import re
import time
import threading


class Terminal:
    """Class formatting messages using colorama to specific visual tokens.

    If :mod:`Colorama` is not found, it will still work, but without colors.

    Depends on :mod:`Colorama`
    Using **OPENPYPE_LOG_NO_COLORS** environment variable.
    """

    # Is Terminal initialized
    _initialized = False
    # Thread lock for initialization to avoid race conditions
    _init_lock = threading.Lock()
    # Use colorized output
    use_colors = True
    # Output message replacements mapping - set on initialization
    _sdict = {}

    @staticmethod
    def _initialize():
        """Initialize Terminal class as object.

        First check if colorized output is disabled by environment variable
        `OPENPYPE_LOG_NO_COLORS` value. By default is colorized output turned
        on.

        Then tries to import python module that do the colors magic and create
        it's terminal object. Colorized output is not used if import of python
        module or terminal object creation fails.

        Set `_initialized` attribute to `True` when is done.
        """

        from openpype.lib import env_value_to_bool
        log_no_colors = env_value_to_bool(
            "OPENPYPE_LOG_NO_COLORS", default=None
        )
        if log_no_colors is not None:
            Terminal.use_colors = not log_no_colors

        if not Terminal.use_colors:
            Terminal._initialized = True
            return

        try:
            # Try to import `blessed` module and create `Terminal` object
            import blessed
            term = blessed.Terminal()

        except Exception:
            # Do not use colors if crashed
            Terminal.use_colors = False
            print(
                "Module `blessed` failed on import or terminal creation."
                " Pype terminal won't use colors."
            )
            Terminal._initialized = True
            return

        # shortcuts for blessed codes
        _SB = term.bold
        _RST = ""
        _LR = term.tomato2
        _LG = term.aquamarine3
        _LB = term.turquoise2
        _LM = term.slateblue2
        _LY = term.gold
        _R = term.red
        _G = term.green
        _B = term.blue
        _C = term.cyan
        _Y = term.yellow
        _W = term.white

        # dictionary replacing string sequences with colorized one
        Terminal._sdict = {
            r">>> ": _SB + _LG + r">>> " + _RST,
            r"!!!(?!\sCRI|\sERR)": _SB + _R + r"!!! " + _RST,
            r"\-\-\- ": _SB + _C + r"--- " + _RST,
            r"\*\*\*(?!\sWRN)": _SB + _LY + r"***" + _RST,
            r"\*\*\* WRN": _SB + _LY + r"*** WRN" + _RST,
            r"  \- ": _SB + _LY + r"  - " + _RST,
            r"\[ ": _SB + _LG + r"[ " + _RST,
            r" \]": _SB + _LG + r" ]" + _RST,
            r"{": _LG + r"{",
            r"}": r"}" + _RST,
            r"\(": _LY + r"(",
            r"\)": r")" + _RST,
            r"^\.\.\. ": _SB + _LR + r"... " + _RST,
            r"!!! ERR: ":
                _SB + _LR + r"!!! ERR: " + _RST,
            r"!!! CRI: ":
                _SB + _R + r"!!! CRI: " + _RST,
            r"(?i)failed": _SB + _LR + "FAILED" + _RST,
            r"(?i)error": _SB + _LR + "ERROR" + _RST
        }

        Terminal._SB = _SB
        Terminal._RST = _RST
        Terminal._LR = _LR
        Terminal._LG = _LG
        Terminal._LB = _LB
        Terminal._LM = _LM
        Terminal._LY = _LY
        Terminal._R = _R
        Terminal._G = _G
        Terminal._B = _B
        Terminal._C = _C
        Terminal._Y = _Y
        Terminal._W = _W

        Terminal._initialized = True

    @staticmethod
    def _multiple_replace(text, adict):
        """Replace multiple tokens defined in dict.

        Find and replace all occurrences of strings defined in dict is
        supplied string.

        Args:
            text (str): string to be searched
            adict (dict): dictionary with `{'search': 'replace'}`

        Returns:
            str: string with replaced tokens

        """
        for r, v in adict.items():
            text = re.sub(r, v, text)

        return text

    @staticmethod
    def echo(message):
        """Print colorized message to stdout.

        Args:
            message (str): Message to be colorized.
            debug (bool):

        Returns:
            str: Colorized message.

        """
        colorized = Terminal.log(message)
        print(colorized)

        return colorized

    @staticmethod
    def log(message):
        """Return color formatted message.

        If environment variable `OPENPYPE_LOG_NO_COLORS` is set to
        whatever value, message will be formatted but not colorized.

        Args:
            message (str): Message to be colorized.

        Returns:
            str: Colorized message.

        """
        T = Terminal
        # Initialize if not yet initialized and use thread lock to avoid race
        # condition issues
        if not T._initialized:
            # Check if lock is already locked to be sure `_initialize` is not
            # executed multiple times
            if not T._init_lock.locked():
                with T._init_lock:
                    T._initialize()
            else:
                # If lock is locked wait until is finished
                while T._init_lock.locked():
                    time.sleep(0.1)

        # if we dont want colors, just print raw message
        if not T.use_colors:
            return message

        message = re.sub(r'\[(.*)\]', '[ ' + T._SB + T._W +
                         r'\1' + T._RST + ' ]', message)
        message = T._multiple_replace(message + T._RST, T._sdict)

        return message
