#!/usr/bin/env python

import os
import pyblish.api
import opentimelineio as otio
from pathlib import Path
from openpype.pipeline import publish
import requests
import re
from pathlib import PureWindowsPath, PurePosixPath
class IntegrateOpenclip(publish.Extractor):
    """
    Automatically create an openclip based on our existing image sequence
    """

    label = "Integrate Openclip"
    order = pyblish.api.IntegratorOrder + 0.45
    families = ["render", "plate"]
    hosts = ["nuke", "traypublisher", "standalonepublisher"]

    def process(self, instance):
        supported_exts = ['jpg', 'exr', 'hdr', 'raw', 'dpx', 'png', 'jpeg']
        instance_repres = instance.data.get("representations")
        clippable_reps = [rep for rep in instance_repres
                          if 'files' in rep.keys() and 'ext' in rep.keys() and rep['ext'] in supported_exts]
        self.log.info(clippable_reps)
        self.log.info(instance.data)
        if len(clippable_reps) < 1:
            self.log.info('No image sequences to make openclip from')
            return
        #anatomy = instance.context.data['anatomy']
        #filled = anatomy.format(instance.context.data)
        #workf = filled['work']['folder']
        workf = instance.data['publishDir']
        #remove version
        workf = Path(workf).parents[0]
        self.log.info(workf)
        if not os.path.isdir(workf):
            os.makedirs(workf)

        # convert to posix
        posix = str(PurePosixPath(workf)).replace('P:\\', '/Volumes/production').replace('D:\\','/Volumes/production')
        self.log.info(posix)
        self.log.info(clippable_reps[0]['files'])
        self.log.info('number clippable reps: ' + str(len(clippable_reps)))
        self.log.info('clip at ' + str(posix) + '/' + instance.data['asset'] + '.clip')
        pattern = clippable_reps[0]['published_path']
        ext = clippable_reps[0]['ext']
        patternPosix = str(PurePosixPath(pattern)).replace('P:', '/Volumes/production').replace('D:','/Volumes/production')
        patternStripped = os.path.splitext(patternPosix)[0]
        wildcard = re.sub('[0-9]+$','{frame}',patternStripped)
        versions = re.sub('v[0-9]+', 'v{version}',wildcard)
        self.log.info(versions)
        res = requests.post('http://pype-db.local:4040', json={'output': str(posix) + '/' + instance.data['asset'] + '.clip','pattern':versions + '.' + ext})
        if not res:
            self.log.info("Openclip not created")
            return
        self.log.info(res)
