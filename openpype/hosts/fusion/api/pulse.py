import os
import sys

from Qt import QtCore


class PulseThread(QtCore.QThread):
    no_response = QtCore.Signal()

    def __init__(self, parent=None):
        super(PulseThread, self).__init__(parent=parent)

    def run(self):
        app = getattr(sys.modules["__main__"], "app", None)

        # Interval in milliseconds
        interval = os.environ.get("OPENPYPE_FUSION_PULSE_INTERVAL", 1000)

        while True:
            if self.isInterruptionRequested():
                return
            try:
                app.Test()
            except Exception:
                self.no_response.emit()

            self.msleep(interval)


class FusionPulse(QtCore.QObject):
    """A Timer that checks whether host app is still alive.

    This checks whether the Fusion process is still active at a certain
    interval. This is useful due to how Fusion runs its scripts. Each script
    runs in its own environment and process (a `fusionscript` process each).
    If Fusion would go down and we have a UI process running at the same time
    then it can happen that the `fusionscript.exe` will remain running in the
    background in limbo due to e.g. a Qt interface's QApplication that keeps
    running infinitely.

    Warning:
        When the host is not detected this will automatically exit
        the current process.

    """

    def __init__(self, parent=None):
        super(FusionPulse, self).__init__(parent=parent)
        self._thread = PulseThread(parent=self)
        self._thread.no_response.connect(self.on_no_response)

    def on_no_response(self):
        print("Pulse detected no response from Fusion..")
        sys.exit(1)

    def start(self):
        self._thread.start()

    def stop(self):
        self._thread.requestInterruption()
