import os
import sys
import pype_tray

app = pype_tray.PypeTrayApplication()
if os.name == "nt":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        u"pype_tray"
    )

sys.exit(app.exec_())
