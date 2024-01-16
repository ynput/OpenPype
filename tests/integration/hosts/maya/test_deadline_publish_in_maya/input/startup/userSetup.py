import sys
print("\n".join(sys.path))

from maya import cmds
import pyblish.util
import openpype

print("starting OpenPype usersetup for testing")
cmds.evalDeferred("pyblish.util.publish()")

cmds.evalDeferred("cmds.quit(force=True)")
cmds.evalDeferred("cmds.quit")
print("finished OpenPype usersetup  for testing")
