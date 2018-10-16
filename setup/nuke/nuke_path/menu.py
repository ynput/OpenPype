import nuke
# auto fix version paths in write nodes following root name of script
cmd = '''
import re
rootVersion=re.search('[vV]\d+', os.path.split(nuke.root().name())[1]).group()
for each in nuke.allNodes():
    if each.Class() == 'Write':
        each['file'].setValue(re.sub('[vV]\d+', rootVersion, each['file'].value()))
'''
nuke.knobDefault('onScriptSave', cmd)
print '\n>>> menu.py: Function for automatic check of version in write nodes is added\n'

ffmpeg_cmd = '''if nuke.env['LINUX']:
  nuke.tcl('load ffmpegReader')
  nuke.tcl('load ffmpegWriter')
else:
  nuke.tcl('load movReader')
  nuke.tcl('load movWriter')'''
nuke.knobDefault('onScriptLoad', ffmpeg_cmd)


# # run avalon's tool Workfiles
# workfiles = '''from avalon.tools import workfiles
# if nuke.Root().name() == 'Root':
#     nuke.scriptClose()
# workfiles.show(os.environ["AVALON_WORKDIR"])'''
# nuke.knobDefault('onCreate', workfiles)
