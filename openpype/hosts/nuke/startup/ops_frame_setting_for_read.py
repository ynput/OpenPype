import nuke
import nukescripts
import re


class FrameSettingsPanel(nukescripts.PythonPanel):
    def __init__(self, node):
        nukescripts.PythonPanel.__init__(self, 'Frame Range')
        self.read_node = node
        # CREATE KNOBS
        self.range = nuke.String_Knob('fRange', 'Frame Range', '%s-%s' %
                                      (nuke.root().firstFrame(),
                                       nuke.root().lastFrame()))
        self.selected = nuke.Boolean_Knob("selection")
        self.info = nuke.Help_Knob("Instruction")
        # ADD KNOBS
        self.addKnob(self.selected)
        self.addKnob(self.range)
        self.addKnob(self.info)
        self.selected.setValue(False)

    def knobChanged(self, knob):
        frame_range = self.range.value()
        pattern = r"^(?P<start>-?[0-9]+)(?:(?:-+)(?P<end>-?[0-9]+))?$"
        match = re.match(pattern, frame_range)
        frame_start = int(match.group("start"))
        frame_end = int(match.group("end"))
        if not self.read_node:
            return
        for r in self.read_node:
            if self.onchecked():
                if not nuke.selectedNodes():
                    return
                if r in nuke.selectedNodes():
                    r["frame_mode"].setValue("start_at")
                    r["frame"].setValue(frame_range)
                    r["first"].setValue(frame_start)
                    r["last"].setValue(frame_end)
            else:
                r["frame_mode"].setValue("start_at")
                r["frame"].setValue(frame_range)
                r["first"].setValue(frame_start)
                r["last"].setValue(frame_end)

    def onchecked(self):
        if self.selected.value():
            return True
        else:
            return False
