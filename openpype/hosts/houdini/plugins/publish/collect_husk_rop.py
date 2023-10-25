import re
import os

import hou
import pyblish.api

from openpype.hosts.houdini.api.lib import (
    evalParmNoFrame,
    get_color_management_preferences
)
from openpype.hosts.houdini.api import (
    colorspace
)


class CollectHuskROPProducts(pyblish.api.InstancePlugin):
    """Collect Husk Products

    Collects the instance.data["files"] for the render products.

    Provides:
        instance    -> files

    """

    label = "Husk ROP Products"
    order = pyblish.api.CollectorOrder + 0.4
    hosts = ["houdini"]
    families = ["husk"]

    def process(self, instance):

        rop = hou.node(instance.data.get("instance_node"))
        
        self.log.debug("Instance data: %s" % instance.data)

        # Collect chunkSize
        chunk_size_parm = rop.parm("chunkSize")
        if chunk_size_parm:
            chunk_size = int(chunk_size_parm.eval())
            instance.data["chunkSize"] = chunk_size
            self.log.debug("Chunk Size: %s" % chunk_size)

            default_prefix = evalParmNoFrame(rop, "outputimage")
            render_products = []

            # Default beauty AOV
            beauty_product = self.get_render_product_name(
                prefix=default_prefix, suffix=None
            )
            render_products.append(beauty_product)

            files_by_aov = {
                "beauty": self.generate_expected_files(instance,
                                                       beauty_product)
            }


        for product in render_products:
            self.log.debug("Found render product: %s" % product)

        filenames = list(render_products)
        instance.data["files"] = filenames
        instance.data["renderProducts"] = colorspace.ARenderProduct()

        # For now by default do NOT try to publish the rendered output
        instance.data["publishJobState"] = "Suspended"
        instance.data["attachTo"] = []      # stub required data

        if "expectedFiles" not in instance.data:
            instance.data["expectedFiles"] = list()
        instance.data["expectedFiles"].append(files_by_aov)

        # update the colorspace data
        colorspace_data = get_color_management_preferences()
        instance.data["colorspaceConfig"] = colorspace_data["config"]
        instance.data["colorspaceDisplay"] = colorspace_data["display"]
        instance.data["colorspaceView"] = colorspace_data["view"]
        
        instance.data["huskCommandline"] = self.submit(rop, instance)

    def get_render_product_name(self, prefix, suffix):
        product_name = prefix
        if suffix:
            # Add ".{suffix}" before the extension
            prefix_base, ext = os.path.splitext(prefix)
            product_name = prefix_base + "." + suffix + ext

        return product_name

    def generate_expected_files(self, instance, path):
        """Create expected files in instance data"""

        dir = os.path.dirname(path)
        file = os.path.basename(path)

        if "#" in file:
            def replace(match):
                return "%0{}d".format(len(match.group()))

            file = re.sub("#+", replace, file)

        if "%" not in file:
            return path

        expected_files = []
        start = instance.data["frameStart"]
        end = instance.data["frameEnd"]
        for i in range(int(start), (int(end) + 1)):
            expected_files.append(
                os.path.join(dir, (file % i)).replace("\\", "/"))

        return expected_files

    def _generate_command(self, node, instance):
        chunkSize = node.parm('chunkSize').eval()
        renderer = node.parm('renderer')
        self.log.debug("renderer: %s" % renderer)
        verbosity = node.parm('verbosity').eval()
        
        usdfile = "the_path_for_usdfile.usd"
        self.log.debug("usdfile: %s" % usdfile)
        
        start = instance.data["frameStart"]
        end = instance.data["frameEnd"]
        inc = instance.data["byFrameStep"]
        
        output = node.parm('outputimage').eval()
        output = output[:-8] + '%04d.exr'
        
        outputDir = output.split('/')[:-1]
        outputDir = '/'.join(outputDir)
        
        if not os.path.exists(outputDir):
            os.makedirs(outputDir)
        
        self.log.debug("output: %s" % output)
        
        rendererLabel = renderer.eval()
        self.log.debug("rendererLabel: %s" % rendererLabel)
        
        framesToRender = float(end - start) / inc
        if framesToRender < chunkSize:
            chunkSize = math.ceil(framesToRender)
        self.log.debug("chunkSize: %s" % chunkSize)
        
        if os.name == 'nt':
            husk_bin = 'husk.exe'
        else:
            hfs = hou.getenv('HFS')
            if hfs:
                husk_bin = hfs + '/bin/husk'
            else:
                print("$HFS variable is not set. It's required for running Husk command.")
                raise ValueError('HFS missing')
                
        command = []
        command.append(husk_bin)
        command.append('-R %s' % rendererLabel)
        command.append('-f <STARTFRAME>')
        command.append('-n %s' % chunkSize)
        command.append('-i %s' % inc)
        command.append('-Va%s' % verbosity)
        command.append('-o %s' % output)
        command.append('--make-output-path')
        command.append('--exrmode 0')
        command.append('--snapshot 60')
        command.append('--snapshot-suffix ""')
        command.append(usdfile)
        command = ' '.join(command)
        
        self.log.debug("command: %s" % command)
        
        return command
    
    def submit(self, rop_node, instance):
        print("submitting")
        node = rop_node
        self.log.debug("Node: %s" % node)
        # batch = node.parm('batch').eval()
        # comment = node.parm('comment').eval()
        # priority = node.parm('priority').eval()
        # suspended = node.parm('submitsuspended').eval()
        
        checks = run_checks()
        
        self.log.debug("checks: %s" % checks)
        
        command = self._generate_command(rop_node, instance)
        self.log.debug("command: %s" % command)
        
        if checks:
            nodes = []
            nodes = traverseInputs(node, nodes)
            if nodes:
                updateMode = hou.updateModeSetting()
                hou.setUpdateMode(hou.updateMode.Manual)
                prep_deadline()
                hou.hipFile.save()
                batch += ' - ' + strftime("%H:%M", localtime())
                for node in nodes:
                    # executeLocally
                    try:
                        executeLocally = node.parm('executelocally').eval()
                    except:
                        executeLocally = None
                        
                    # sections
                    try:
                        sections = node.parm("sections").eval()
                    except:
                        sections = None
                        
                    print('-------------------')
                    print(node)
                    print(executeLocally)
                    print(sections)
                    
                    if sections:
                        start = node.parm('sectionrange1').eval()
                        end = node.parm('sectionrange2').eval()
                        reader = hou.node(node.parm("readerpath").eval())
                        currentSectionParm = reader.parm('currentsection')
                        currentSection = currentSectionParm.eval()
                        
                        for section in range(start, end + 1):
                            currentSectionParm.set(section)
                            if executeLocally == True:
                                node.render()
                            else:
                                node.hdaModule().writeSubmissionFiles(node, section, batch, comment, priority, suspended)
                        currentSectionParm.set(currentSection)
                    else:
                        if executeLocally == True:
                            frameRange = hou.playbar.frameRange()
                            playbackRange = hou.playbar.playbackRange()
                            frame = hou.frame()
                            
                            start = node.parm('f1').eval()
                            end = node.parm('f2').eval()
                            
                            hou.playbar.setFrameRange(start, end)
                            hou.playbar.setPlaybackRange(start, end)
                            hou.setFrame(start)
                            
                            node.render()
                            
                            hou.playbar.setFrameRange(frameRange[0], frameRange[1])
                            
                            hou.playbar.setPlaybackRange(playbackRange[0], playbackRange[1])
                            hou.setFrame(frame)
                        else:
                            node.hdaModule().writeSubmissionFiles(node, None, batch, comment, priority, suspended)
                send_deadline()
                hou.setUpdateMode(updateMode)
                hou.node('.').parm('comment').set('')
                

import os
import sys
import shutil
import subprocess
from time import localtime, strftime


allowedNodes = ['cacher', 'cache_usd', 'husk']

    
def collectInputs2():
    node = hou.node('.')
    nodes = []
    nodes = traverseInputs(node, nodes)
    for node in nodes:
        print(node)


def traverseInputs(node, nodes):
    if node.isBypassed():
        inputs = [node.input(0)]
    elif node.type().name() == 'switch':
        index = node.parm('index').eval()
        inputs = [node.input(index)]
    else:
        inputs = node.inputs()
        
    for input in inputs:
        if input:
            nodes = traverseInputs(input, nodes)
            if not input.isBypassed():
                if input.type().nameComponents()[2] in allowedNodes:
                    if input not in nodes:
                        nodes.append(input)
    return nodes


def prep_deadline():
    # delete files in deadline folder
    tempFolder = os.path.join(hou.getenv('JOB'), 'houdini/deadline')
    if os.path.exists(tempFolder):
        shutil.rmtree(tempFolder)
        os.makedirs(tempFolder)
    else:
        os.makedirs(tempFolder)

    args_file = os.path.join(tempFolder, 'args.txt')
    
    # args file
    args = []
    args.append('-SubmitMultipleJobs')
    args.append('-dependent')

    f = open(args_file, "w")
    f.write('\n'.join(args))
    f.close()
    
    
def get_deadline_command():
    deadline_bin = ""
    try:
        deadline_bin = os.environ['DEADLINE_PATH']
    except KeyError:
        pass

    if deadline_bin == "" and os.path.exists( "/Users/Shared/Thinkbox/DEADLINE_PATH" ):
        with open( "/Users/Shared/Thinkbox/DEADLINE_PATH" ) as f:
            deadline_bin = f.read().strip()

    deadline_command = os.path.join(deadline_bin, "deadlinecommand")
    return deadline_command
    
    
def send_deadline():
    deadline_command = get_deadline_command()
    tempFolder = os.path.join(hou.getenv('JOB'), 'houdini/deadline')
    if not os.path.exists(tempFolder):
        os.makedirs(tempFolder)
    
    args_file = os.path.join(tempFolder, 'args.txt')
    
    startupinfo = None
    creationflags = 0
    if os.name == 'nt':
        creationflags = subprocess.CREATE_NO_WINDOW

    arguments = [deadline_command, args_file]

    process = subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, creationflags=creationflags)

    output = ""
    output, errors = process.communicate()

    if sys.version_info[0] > 2 and type(output) == bytes:
        output = output.decode()
    
    print(output)
    return output
    
def run_checks():
    job = hou.getenv('JOB')
    
    if '\\' in job:
        hou.ui.displayMessage('JOB env variable contains \ character. Please replace it with /')
        return False
    return True
    
            
import os
import sys
import subprocess
import shutil
import math


def printCommand():
    node = hou.pwd()
    command = generateCommand(node)
    print(command)

def renderLocally():
    print('dd')
    
def findShotSubnet():
    node = hou.node(".")
    path = node.path()
    path = path.split('/')[:3]
    path = '/'.join(path)
    shotSubnet = hou.node(path)
    if shotSubnet.parmTemplateGroup().findFolder('Shot Info'):
        return shotSubnet
    else:
        return None
        
        
def explore():
    node = hou.node(".")
    output = node.parm("output").eval()
    output = output.split('/')[:-1]
    output = '/'.join(output)
    if os.path.isdir(output):
        if sys.platform == "win32":
            os.startfile(output)
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, output])
    
        
def remove():
    node = hou.node(".")
    output = node.parm("output").eval()
    output = output.split('/')[:-1]
    output = '/'.join(output)
    if os.path.isdir(output):
        choice = hou.ui.displayMessage('Remove this version?\n' + output, buttons=('OK', 'Cancel'))
        if choice == 0:
            shutil.rmtree(output)
            node.cook(True)
        
            
def generateCommand(node):
    chunkSize = node.parm('chunksize').eval()
    renderer = node.parm('renderer')
    verbosity = node.parm('verbosity').eval()
    usdfile = node.parm('usdfile').eval()
    start = node.parm('f1').eval()
    end = node.parm('f2').eval()
    inc = node.parm('f3').eval()

    output = node.parm('output').eval()
    output = output[:-8] + '%04d.exr'
    
    outputDir = output.split('/')[:-1]
    outputDir = '/'.join(outputDir)
    
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
    
    rendererParmIdx = renderer.eval()
    rendererParmLabels = renderer.menuItems()
    rendererLabel = rendererParmLabels[rendererParmIdx]
    
    framesToRender = float(end - start) / inc
    if framesToRender < chunkSize:
        chunkSize = math.ceil(framesToRender)
        
    
    if os.name == 'nt':
        husk_bin = 'husk.exe'
    else:
        hfs = hou.getenv('HFS')
        if hfs:
            husk_bin = hfs + '/bin/husk'
        else:
            print("$HFS variable is not set. It's required for running Husk command.")
            raise ValueError('HFS missing')

            
    command = []
    command.append(husk_bin)
    command.append('-R %s' % rendererLabel)
    command.append('-f <STARTFRAME>')
    command.append('-n %s' % chunkSize)
    command.append('-i %s' % inc)
    command.append('-Va%s' % verbosity)
    command.append('-o %s' % output)
    command.append('--make-output-path')
    command.append('--exrmode 0')
    command.append('--snapshot 60')
    command.append('--snapshot-suffix ""')
    command.append(usdfile)
    command = ' '.join(command)
    
    return command

def generateCommand_PSB(node):
    chunkSize = node.parm('chunksize').eval()
    renderer = node.parm('renderer')
    verbosity = node.parm('verbosity').eval()
    usdfile = node.parm('usdfile').eval()
    start = node.parm('f1').eval()
    end = node.parm('f2').eval()
    inc = node.parm('f3').eval()

    output = node.parm('output').eval()
    output = output[:-8] + '####.exr'
    
    outputDir = output.split('/')[:-1]
    outputDir = '/'.join(outputDir)
    
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
    
    rendererParmIdx = renderer.eval()
    rendererParmLabels = renderer.menuItems()
    rendererLabel = rendererParmLabels[rendererParmIdx]
    
    framesToRender = float(end - start) / inc
    if framesToRender < chunkSize:
        chunkSize = math.ceil(framesToRender)
        
    
    if os.name == 'nt':
        husk_bin = 'husk.exe'
    else:
        hfs = hou.getenv('HFS')
        if hfs:
            husk_bin = hfs + '/bin/husk'
        else:
            print("$HFS variable is not set. It's required for running Husk command.")
            raise ValueError('HFS missing')

            
    command = []
    command.append('%s' % output.replace("/", "\\"))
    command = ' '.join(command)
    
    return command
    
def writeSubmissionFiles(node, section=None, batch='', comment='', priority=50, suspended=False):
    start = node.parm('f1').eval()
    end = node.parm('f2').eval()
    inc = node.parm('f3').eval()
    chunkSize = node.parm('chunksize').eval()
    concurrent = node.parm('concurrent').eval()
    name = node.name()
    elementName = node.parm('name').eval()
    version = node.parm('version').eval()
    output = node.parm('output').eval()
    enable_psb = node.parm('enable_psb').eval()
    
    # deadline folder
    tempFolder = os.path.join(hou.getenv('JOB'), 'houdini/deadline')
    if not os.path.exists(tempFolder):
        os.makedirs(tempFolder)
    
    args_file = os.path.join(tempFolder, 'args.txt')

    husk_script = os.path.join(hou.getenv('VFXTRICKS'), 'scripts', 'run_husk.py')
    
    # this is what I mean about hardcoded real
    # we must refactore this provide a way to track externally
    # for that reason we added cc_utils module -- WIP
    
    # husk_script = 'R:\\HSITE\\houdini19.5\\packages\\VFXTricks\\scripts\\run_husk.py'
    husk_script = 'R:\\HSITE\\WORKGROUPS\\houdini19.5\\VFXTricks\scripts\\run_husk.py'
    logToggle = node.parm('logToggle').eval()
    logFolder = node.parm('logFolder').eval()
    
    # add padding to outputFilename
    outputFilename = output.split('/')
    filename = outputFilename[-1]
    filename = filename.split('.')
    filename = filename[0] + '.####.' + filename[2]
    outputFilename[-1] = filename
    outputFilename = '/'.join(outputFilename)

    # remove filename from output
    outputDirectory = output.split('/')
    outputDirectory = '/'.join(outputDirectory[:-1])
    outputDirectory += '/'
    
    # job file
    job_info_file = os.path.join(tempFolder, name + '_info.txt')
    job_info = []
    job_info.append('Plugin=HuskVFXTricks')
    job_info.append('Frames=%s-%sx%s' % (start, end, 1))
    
    if inc == 1:
        job_info.append('ChunkSize=%s' % (chunkSize))
    else:
        job_info.append('ChunkSize=%s' % (chunkSize*inc))
        
    job_info.append('ConcurrentTasks=%s' % concurrent)
    job_info.append('Name=%s' % (elementName + '_v' + ('%03d' % (version + 1))))
    job_info.append('BatchName=%s' % batch)
    job_info.append('Comment=%s' % comment)
    job_info.append('ConcurrentTasks=%s' % concurrent)
    job_info.append('Priority=%s' % priority)
    job_info.append('OutputFilename0=%s' % outputFilename)
    # hardcoded values for pool and group  for Husk
    job_info.append('Group=usd')
    job_info.append('Pool=cowfarm-1-inst')

    if suspended:
        job_info.append('InitialStatus=Suspended')
    
    
    f = open(job_info_file, "w")
    f.write('\n'.join(job_info))
    f.close()
    
    # job file 2 -- adittional to run PSB
    job_info_file_PSB = os.path.join(tempFolder, name + '_info_PSB.txt')
    job_info_PSB = []
    job_info_PSB.append('Plugin=PSB')
    job_info_PSB.append('Frames=%s-%sx%s' % (start, end, 1))
    
    if inc == 1:
        job_info_PSB.append('ChunkSize=%s' % (chunkSize))
    else:
        job_info_PSB.append('ChunkSize=%s' % (chunkSize*inc))
        
    job_info_PSB.append('ConcurrentTasks=%s' % concurrent)
    job_info_PSB.append('Name=%s' % (elementName + '_v' + ('%03d' % (version + 1))) + "-PSB")
    job_info_PSB.append('BatchName=%s' % batch)
    job_info_PSB.append('Comment=%s' % comment)
    job_info_PSB.append('ConcurrentTasks=%s' % concurrent)
    job_info_PSB.append('Priority=%s' % priority)
    job_info_PSB.append('OutputFilename0=%s' % outputFilename)
    # hardcoded values for pool and group  for Husk
#    job_info_PSB.append('Group=usd')
    job_info_PSB.append('Pool=psb')

    if suspended:
        job_info_PSB.append('InitialStatus=Suspended')
    
    
    f = open(job_info_file_PSB, "w")
    f.write('\n'.join(job_info_PSB))
    f.close()
    
    # plugin file
    job_plugin_file = os.path.join(tempFolder, name + '_plugin.txt')
    job_plugin = []
    
    job_plugin.append('ScriptFile=%s' % husk_script)
    #job_plugin.append('Version=2.7')
    #job_plugin.append('ShellExecute=True')
    #job_plugin.append('Shell=cmd')
    
#    if os.name == 'nt':
#        job_plugin.append('Executable=python.exe')
#    else:
#        job_plugin.append('Executable=python')
        
    args = []
    #args.append(husk_script)
    args.append(generateCommand(node))
    args.append('-e <ENDFRAME>')
    if logToggle:
        args.append('-log %s' % logFolder)
    args = ' '.join(args)
    
    job_plugin.append('Arguments=%s' % args)
            
    f = open(job_plugin_file, "w")
    f.write('\n'.join(job_plugin))
    f.close()

    # plugin file for PSB ####
    job_plugin_file_PSB = os.path.join(tempFolder, name + '_plugin_PSB.txt')
    job_plugin_PSB = []
    
#    job_plugin_PSB.append('ScriptFile=%s' % husk_script)
    #job_plugin.append('Version=2.7')
    #job_plugin.append('ShellExecute=True')
    #job_plugin.append('Shell=cmd')
    
#    if os.name == 'nt':
#        job_plugin.append('Executable=python.exe')
#    else:
#        job_plugin.append('Executable=python')
        
    args = []
    #args.append(husk_script)
    args.append(generateCommand_PSB(node))
#    args.append('-e <ENDFRAME>')
#    if logToggle:
#        args.append('-log %s' % logFolder)
    args = ' '.join(args)
    
    job_plugin_PSB.append('InputFile=%s' % args)
            
    f = open(job_plugin_file_PSB, "w")
    f.write('\n'.join(job_plugin_PSB))
    f.close()
    
    
    # appends args file
    f = open(args_file, "a")
    f.write('\n' + '-job')
    f.write('\n' + job_info_file)
    f.write('\n' + job_plugin_file)
    # add additional job here below in case we select PSB
    if enable_psb:
        f.write('\n' + '-job')
        f.write('\n' + job_info_file_PSB)
        f.write('\n' + job_plugin_file_PSB)
    f.close()