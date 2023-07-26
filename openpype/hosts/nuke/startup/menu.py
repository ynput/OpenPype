from openpype.pipeline import install_host
from openpype.hosts.nuke.api import NukeHost

host = NukeHost()
install_host(host)

# TODO horent:old heck with output format, see hornet commit 153ccd9
import nuke
import os

import DeadlineNukeClient

from openpype.lib import Logger
from openpype.hosts.nuke import api
from openpype.hosts.nuke.api.lib import (
    on_script_load,
    check_inventory_versions,
    WorkfileSettings,
    dirmap_file_name_filter,
    add_scripts_gizmo
)
from openpype.settings import get_project_settings

log = Logger.get_logger(__name__)



# fix ffmpeg settings on script

# set checker for last versions on loaded containers

log.info('Automatic syncing of write file knob to script version')



# Hornet- helper to switch file extension to filetype
def writes_ver_sync():
    ''' Callback synchronizing version of publishable write nodes
    '''
    try:
	print('Hornet- syncing version to write nodes')
        #rootVersion = pype.get_version_from_path(nuke.root().name())
        pattern = re.compile(r"[\._]v([0-9]+)", re.IGNORECASE)
        rootVersion = pattern.findall(nuke.root().name())[0]
        padding = len(rootVersion)
        new_version = "v" + str("{" + ":0>{}".format(padding) + "}").format(
            int(rootVersion)
        )
        print("new_version: {}".format(new_version))
    except Exception as e:
        print(e)
        return
    groupnodes = [node.nodes() for node in nuke.allNodes() if node.Class() == 'Group']
    allnodes = [node for group in groupnodes for node in group] + nuke.allNodes()
    print(allnodes)
    for each in allnodes:
        print('node')
        if each.Class() == 'Write':
            # check if the node is avalon tracked
            if each.name().startswith('inside_'):
                avalonNode = nuke.toNode(each.name().replace('inside_',''))
            else:
                avalonNode = each
            if "AvalonTab" not in avalonNode.knobs():
                print("tab failure")
                continue

            avalon_knob_data = avalon.nuke.get_avalon_knob_data(
                avalonNode, ['avalon:', 'ak:'])
            try:
                if avalon_knob_data['families'] not in ["render", "write"]:
                    print("families fail")
                    log.debug(avalon_knob_data['families'])
                    continue

                node_file = each['file'].value()

                #node_version = "v" + pype.get_version_from_path(node_file)
                node_version = 'v' + pattern.findall(node_file)[0]

                log.debug("node_version: {}".format(node_version))

                node_new_file = node_file.replace(node_version, new_version)
                each['file'].setValue(node_new_file)
                #H: don't need empty folders if work file isn't rendered later
                #if not os.path.isdir(os.path.dirname(node_new_file)):
                #    log.warning("Path does not exist! I am creating it.")
                #    os.makedirs(os.path.dirname(node_new_file), 0o766)
            except Exception as e:
                print(e)
                log.warning(
                    "Write node: `{}` has no version in path: {}".format(
                        each.name(), e))


def switchExtension():
    nde = nuke.thisNode()
    knb = nuke.thisKnob()
    if knb == nde.knob('file_type'):
        filek = nde.knob('file')
        old = filek.value()
        pre,ext = os.path.splitext(old)
        filek.setValue(pre + '.' + knb.value())
knobMatrix = { 'exr': ['colorspace', 'write_ACES_compliant_EXR', 'autocrop', 'datatype', 'heroview', 'metadata', 'interleave'],
		'png': ['colorspace', 'datatype'],
		'tiff': ['colorspace','datatype', 'compression'],
		'mov': ['colorspace','mov64_codec', 'mov64_fps', 'mov64_encoder' ]
}
def embedOptions():
    nde = nuke.thisNode()
    knb = nuke.thisKnob()
    log.info(' knob of type' + str(knb.Class()))
    htab = nuke.Tab_Knob('htab','Hornet')
    if knb == nde.knob('file_type'):
        group = nuke.toNode('.'.join(['root'] + nde.fullName().split('.')[:-1]))
        ftype = knb.value()
    else:
        return
	if ftype not in knobMatrix.keys():
		return
    allTrackedKnobs = [ value for sublist in knobMatrix.values() for value in sublist]
    allTrackedKnobs.append("file_type")
    allTrackedKnobs.append("file")
    allTrackedKnobs.append("channels")
    allTrackedKnobs.append("Render Local")
    allLinkedKnobs = [knob for knob in group.allKnobs() if isinstance(knob, nuke.Link_Knob)]
    allTabKnobs = [knob for knob in group.allKnobs() if isinstance(knob, nuke.Tab_Knob)]
    allTextKnobs = [knob for knob in group.allKnobs() if isinstance(knob, nuke.Text_Knob)]
    allScriptKnobs = [knob for knob in group.allKnobs() if isinstance(knob, nuke.PyScript_Knob)]
    allMultiKnobs = [knob for knob in group.allKnobs() if isinstance(knob, nuke.Multiline_Eval_String_Knob)]
    for knob in allLinkedKnobs:
        if knob.name() in allTrackedKnobs:
            group.removeKnob(knob)
    for knob in allTabKnobs:
        if knob.name() in ['beginoutput','endoutput','beginpipeline','beginoutput','endpipeline','htab']:
            group.removeKnob(knob)
    for knob in allScriptKnobs:
        if knob.name() in ["submit","publish", "readfrom"]:
            group.removeKnob(knob)
    for knob in allMultiKnobs:
        if knob.name() == "File output":
            group.removeKnob(knob)
    for knob in allTextKnobs:
        if knob.name() in ['tempwarn','reviewwarn','dlinewarn','div']:
            group.removeKnob(knob)
    while group.knob('htab'):
        group.removeKnob(group.knob('htab'))
    group.addKnob(htab)
    beginGroup = nuke.Tab_Knob('beginoutput', 'Output', nuke.TABBEGINGROUP)
    group.addKnob(beginGroup)

    if 'file' not in group.knobs().keys():
        fle = nuke.Multiline_Eval_String_Knob('File output')
        fle.setText(nde.knob('file').value())
        group.addKnob(fle)
        link = nuke.Link_Knob('channels')
        link.makeLink(nde.name(), 'channels')
        link.setName('channels')
        group.addKnob(link)
        if 'file_type' not in group.knobs().keys():
            link = nuke.Link_Knob('file_type')
            link.makeLink(nde.name(), 'file_type')
            link.setName('file_type')
            link.setFlag(0x1000)
            group.addKnob(link)
        for kname in knobMatrix[ftype]:
            link = nuke.Link_Knob(kname)
            link.makeLink(nde.name(), kname)
            link.setName(kname)
            link.setFlag(0x1000)
            group.addKnob(link)
    endGroup = nuke.Tab_Knob('endoutput', None, nuke.TABENDGROUP)
    group.addKnob(endGroup)
    beginGroup = nuke.Tab_Knob('beginpipeline', 'Rendering and Pipeline', nuke.TABBEGINGROUP)
    group.addKnob(beginGroup)
    sub = nuke.PyScript_Knob('submit', 'Submit to Deadline', "DeadlineNukeClient.main()")
    pub = nuke.PyScript_Knob('publish', 'Publish', "from openpype.tools.utils import host_tools;host_tools.show_publisher(parent=(main_window if nuke.NUKE_VERSION_MAJOR >= 14 else None),tab='Publish')")
    readfrom_src = "import write_to_read;write_to_read.write_to_read(nuke.thisNode(), allow_relative=False)"
    readfrom = nuke.PyScript_Knob('readfrom', 'Read From Rendered', readfrom_src)
    link = nuke.Link_Knob('render')
    link.makeLink(nde.name(), 'Render')
    link.setName('Render Local')
    group.addKnob(link)

    div = nuke.Text_Knob('div','','')
    group.addKnob(sub)
    group.addKnob(readfrom)
    group.addKnob(div)
    group.addKnob(pub)
    tempwarn = nuke.Text_Knob('tempwarn', '', '- all rendered files are TEMPORARY and WILL BE OVERWRITTEN unless published ')
    reviewwarn = nuke.Text_Knob('reviewwarn', '', '- Check "Review" in the OpenPype tab to automatically generate an FTrack Review on Publish')
    dlinewarn = nuke.Text_Knob('dlinewarn', '', '- Deadline Submission settings are available in the Deadline Tab')
    group.addKnob(tempwarn)
    group.addKnob(reviewwarn)
    group.addKnob(dlinewarn)
    endGroup = nuke.Tab_Knob('endpipeline', None, nuke.TABENDGROUP)
    group.addKnob(endGroup)


nuke.addKnobChanged(switchExtension, nodeClass='Write')
nuke.addKnobChanged(embedOptions, nodeClass='Write')
nuke.addOnScriptSave(writes_ver_sync)
