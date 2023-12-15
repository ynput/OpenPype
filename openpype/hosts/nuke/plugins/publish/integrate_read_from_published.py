#!/usr/bin/env python

import os
import pyblish.api
import nuke
class IntegrateReadFromPublish(pyblish.api.InstancePlugin):
    """
    Automatically create an openclip based on our existing image sequence
    """

    label = "Read in Published"
    order = pyblish.api.IntegratorOrder + 0.91
    families = ['render', 'plate']
    hosts = ['nuke']
    def process(self, instance):
        supported_exts = ['jpg', 'exr', 'hdr', 'raw', 'dpx', 'png', 'jpeg','mov','mp4','tiff','tga']
        instance_repres = instance.data.get("representations")
        readable_reps = [rep for rep in instance_repres
                        if 'files' in rep.keys() and 'ext' in rep.keys() and rep['ext'] in supported_exts]
        if len(readable_reps) == 0:
            self.log.info("No Nuke-readable representations found for instance %s" % instance)
            return
        published_path = instance.data['publishDir']
        sequences = nuke.getFileNameList(published_path)
        for seq in sequences:
            # clean frame range hint nuke adds to the end of the filename
            if ' ' in seq: seq = seq.split(' ')[0]
            nde = nuke.createNode('Read')
            nde.knob('file').setValue(os.path.join(published_path, seq).replace('\\', '/'))
            nde.knob('first').setValue(int(instance.data['frameStart']))
            nde.knob('last').setValue(int(instance.data['frameEnd']))
