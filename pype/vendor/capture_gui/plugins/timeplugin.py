import sys
import logging
import re

import maya.OpenMaya as om
from capture_gui.vendor.Qt import QtCore, QtWidgets

import capture_gui.lib
import capture_gui.plugin

log = logging.getLogger("Time Range")


def parse_frames(string):
    """Parse the resulting frames list from a frame list string.

    Examples
        >>> parse_frames("0-3;30")
        [0, 1, 2, 3, 30]
        >>> parse_frames("0,2,4,-10")
        [0, 2, 4, -10]
        >>> parse_frames("-10--5,-2")
        [-10, -9, -8, -7, -6, -5, -2]

    Args:
        string (str): The string to parse for frames.

    Returns:
        list: A list of frames

    """

    result = list()
    if not string.strip():
        raise ValueError("Can't parse an empty frame string.")

    if not re.match("^[-0-9,; ]*$", string):
        raise ValueError("Invalid symbols in frame string: {}".format(string))

    for raw in re.split(";|,", string):

        # Skip empty elements
        value = raw.strip().replace(" ", "")
        if not value:
            continue

        # Check for sequences (1-20) including negatives (-10--8)
        sequence = re.search("(-?[0-9]+)-(-?[0-9]+)", value)

        # Sequence
        if sequence:
            start, end = sequence.groups()
            frames = range(int(start), int(end) + 1)
            result.extend(frames)

        # Single frame
        else:
            try:
                frame = int(value)
            except ValueError:
                raise ValueError("Invalid frame description: "
                                 "'{0}'".format(value))

            result.append(frame)

    if not result:
        # This happens when only spaces are entered with a separator like `,` or `;`
        raise ValueError("Unable to parse any frames from string: {}".format(string))

    return result


class TimePlugin(capture_gui.plugin.Plugin):
    """Widget for time based options"""

    id = "Time Range"
    section = "app"
    order = 30

    RangeTimeSlider = "Time Slider"
    RangeStartEnd = "Start/End"
    CurrentFrame = "Current Frame"
    CustomFrames = "Custom Frames"

    def __init__(self, parent=None):
        super(TimePlugin, self).__init__(parent=parent)

        self._event_callbacks = list()

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(self._layout)

        self.mode = QtWidgets.QComboBox()
        self.mode.addItems([self.RangeTimeSlider,
                            self.RangeStartEnd,
                            self.CurrentFrame,
                            self.CustomFrames])

        frame_input_height = 20
        self.start = QtWidgets.QSpinBox()
        self.start.setRange(-sys.maxint, sys.maxint)
        self.start.setFixedHeight(frame_input_height)
        self.end = QtWidgets.QSpinBox()
        self.end.setRange(-sys.maxint, sys.maxint)
        self.end.setFixedHeight(frame_input_height)

        # unique frames field
        self.custom_frames = QtWidgets.QLineEdit()
        self.custom_frames.setFixedHeight(frame_input_height)
        self.custom_frames.setPlaceholderText("Example: 1-20,25;50;75,100-150")
        self.custom_frames.setVisible(False)

        self._layout.addWidget(self.mode)
        self._layout.addWidget(self.start)
        self._layout.addWidget(self.end)
        self._layout.addWidget(self.custom_frames)

        # Connect callbacks to ensure start is never higher then end
        # and the end is never lower than start
        self.end.valueChanged.connect(self._ensure_start)
        self.start.valueChanged.connect(self._ensure_end)

        self.on_mode_changed()  # force enabled state refresh

        self.mode.currentIndexChanged.connect(self.on_mode_changed)
        self.start.valueChanged.connect(self.on_mode_changed)
        self.end.valueChanged.connect(self.on_mode_changed)
        self.custom_frames.textChanged.connect(self.on_mode_changed)

    def _ensure_start(self, value):
        self.start.setValue(min(self.start.value(), value))

    def _ensure_end(self, value):
        self.end.setValue(max(self.end.value(), value))

    def on_mode_changed(self, emit=True):
        """Update the GUI when the user updated the time range or settings.

        Arguments:
            emit (bool): Whether to emit the options changed signal

        Returns:
            None

        """

        mode = self.mode.currentText()
        if mode == self.RangeTimeSlider:
            start, end = capture_gui.lib.get_time_slider_range()
            self.start.setEnabled(False)
            self.end.setEnabled(False)
            self.start.setVisible(True)
            self.end.setVisible(True)
            self.custom_frames.setVisible(False)
            mode_values = int(start), int(end)
        elif mode == self.RangeStartEnd:
            self.start.setEnabled(True)
            self.end.setEnabled(True)
            self.start.setVisible(True)
            self.end.setVisible(True)
            self.custom_frames.setVisible(False)
            mode_values = self.start.value(), self.end.value()
        elif mode == self.CustomFrames:
            self.start.setVisible(False)
            self.end.setVisible(False)
            self.custom_frames.setVisible(True)
            mode_values = "({})".format(self.custom_frames.text())

            # ensure validation state for custom frames
            self.validate()

        else:
            self.start.setEnabled(False)
            self.end.setEnabled(False)
            self.start.setVisible(True)
            self.end.setVisible(True)
            self.custom_frames.setVisible(False)
            currentframe = int(capture_gui.lib.get_current_frame())
            mode_values = "({})".format(currentframe)

        # Update label
        self.label = "Time Range {}".format(mode_values)
        self.label_changed.emit(self.label)

        if emit:
            self.options_changed.emit()

    def validate(self):
        errors = []

        if self.mode.currentText() == self.CustomFrames:

            # Reset
            self.custom_frames.setStyleSheet("")

            try:
                parse_frames(self.custom_frames.text())
            except ValueError as exc:
                errors.append("{} : Invalid frame description: "
                              "{}".format(self.id, exc))
                self.custom_frames.setStyleSheet(self.highlight)

        return errors

    def get_outputs(self, panel=""):
        """Get the plugin outputs that matches `capture.capture` arguments

        Returns:
            dict: Plugin outputs

        """

        mode = self.mode.currentText()
        frames = None

        if mode == self.RangeTimeSlider:
            start, end = capture_gui.lib.get_time_slider_range()

        elif mode == self.RangeStartEnd:
            start = self.start.value()
            end = self.end.value()

        elif mode == self.CurrentFrame:
            frame = capture_gui.lib.get_current_frame()
            start = frame
            end = frame

        elif mode == self.CustomFrames:
            frames = parse_frames(self.custom_frames.text())
            start = None
            end = None
        else:
            raise NotImplementedError("Unsupported time range mode: "
                                      "{0}".format(mode))

        return {"start_frame": start,
                "end_frame": end,
                "frame": frames}

    def get_inputs(self, as_preset):
        return {"time": self.mode.currentText(),
                "start_frame": self.start.value(),
                "end_frame": self.end.value(),
                "frame": self.custom_frames.text()}

    def apply_inputs(self, settings):
        # get values
        mode = self.mode.findText(settings.get("time", self.RangeTimeSlider))
        startframe = settings.get("start_frame", 1)
        endframe = settings.get("end_frame", 120)
        custom_frames = settings.get("frame", None)

        # set values
        self.mode.setCurrentIndex(mode)
        self.start.setValue(int(startframe))
        self.end.setValue(int(endframe))
        if custom_frames is not None:
            self.custom_frames.setText(custom_frames)

    def initialize(self):
        self._register_callbacks()

    def uninitialize(self):
        self._remove_callbacks()

    def _register_callbacks(self):
        """Register maya time and playback range change callbacks.

        Register callbacks to ensure Capture GUI reacts to changes in
        the Maya GUI in regards to time slider and current frame

        """

        callback = lambda x: self.on_mode_changed(emit=False)

        # this avoid overriding the ids on re-run
        currentframe = om.MEventMessage.addEventCallback("timeChanged",
                                                         callback)
        timerange = om.MEventMessage.addEventCallback("playbackRangeChanged",
                                                      callback)

        self._event_callbacks.append(currentframe)
        self._event_callbacks.append(timerange)

    def _remove_callbacks(self):
        """Remove callbacks when closing widget"""
        for callback in self._event_callbacks:
            try:
                om.MEventMessage.removeCallback(callback)
            except RuntimeError, error:
                log.error("Encounter error : {}".format(error))
