#!/usr/bin/env python

import os
import pyblish.api
import re
import xml.etree.ElementTree as xmlt
class IntegrateOpenclip(pyblish.api.InstancePlugin):
    """
    Automatically create an openclip based on our existing image sequence
    """

    label = "Integrate Openclip"
    order = pyblish.api.IntegratorOrder + 0.91
    families = ['render', 'plate']
    hosts = ['nuke', 'standalonepublisher', 'traypublisher','shell']
    targets = ['local', 'deadline', 'farm_frames', 'farm']
# the pattern based clips are very compact and can reasonably fit here to avoid referencing non python files in the publish steps
    template = r"""<?xml version="1.0"?>
<clip type="clip" version="6">
	<handler>
		<name>MIO Clip</name>
		<version>2</version>
		<options type="dict">
			<ScanPattern type="string"></ScanPattern>
		</options>
	</handler>
</clip>
"""


    def process(self, instance):
        supported_exts = ['jpg', 'exr', 'hdr', 'raw', 'dpx', 'png', 'jpeg','mov','mp4','tiff','tga']
        instance_repres = instance.data.get("representations")
        clippable_reps = [rep for rep in instance_repres
                          if 'files' in rep.keys() and 'ext' in rep.keys() and rep['ext'] in supported_exts]
        sequence = True
        if 'ext' in clippable_reps[0].keys() and clippable_reps[0]['ext'] in ['mov','mp4']:
            sequence = False
        self.log.info(clippable_reps)
        self.log.info(instance_repres)
        if len(clippable_reps) < 1:
            self.log.warn('No media to make openclip from')
            return
        workf = instance.data['publishDir']
        #remove version
        workf = os.path.dirname(os.path.join( os.path.dirname( workf ), '..' ))
        self.log.info(workf)
        if not os.path.isdir(workf):
            os.makedirs(workf)

        # convert to posix
        posix = workf.replace('P:\\', '/Volumes/production/').replace('D:\\','/Volumes/production/').replace('\\','/')
        self.log.info(posix)
        self.log.info(clippable_reps[0]['files'])
        self.log.info('number clippable reps: ' + str(len(clippable_reps)))
        clipPathPosix = str(posix) + '/' + instance.data['asset'] + '_' + instance.data['subset'] + '.clip'
        clipPathWin = str(workf) + '/' + instance.data['asset'] + '_' + instance.data['subset'] + '.clip'
        self.log.info('clip at ' + clipPathWin)
        pattern = clippable_reps[0]['published_path']
        ext = clippable_reps[0]['ext']
        patternPosix = pattern.replace('\\','/').replace('P:', '/Volumes/production').replace('D:','/Volumes/production')
        patternStripped = os.path.splitext(patternPosix)[0]
        if not sequence:
            self.log.info("Not an image sequence, clipping movie file")
            wildcard = patternStripped
            self.log.info(wildcard)
            regex = re.compile('v[0-9]+')
            versions = regex.sub('v{version}', wildcard)
        else:
            wildcard = re.sub('[0-9]+$','{frame}',patternStripped)
            self.log.info(wildcard)
            regex = re.compile('[^a-zA-Z]v[0-9]+[^a-zA-Z]')
            versions = regex.sub(lambda m: m.group().replace(m.group()[1:-1], 'v{version}'),wildcard)
        #versions = re.sub('/v[0-9]+', '/v{version}',wildcard)
        self.log.info(versions)
        #res = requests.post('http://pype-db.local:4040', json={'output': clipPathPosix,'pattern':versions + '.' + ext})
        tree = xmlt.fromstring(self.template)
        patternTag = tree.find('.//ScanPattern')
        patternTag.text = versions + '.' + ext
        with open(clipPathWin, 'wb') as fout:
            fout.write(xmlt.tostring(tree))
            self.log.info("clip file successfully written")
        if not os.path.exists(clipPathWin):
            raise Exception('clip file generation failed')
