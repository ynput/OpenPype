import os
import nuke
import pyblish.api
import re
from datetime import datetime as datetime
class CollectWorkfile(pyblish.api.InstancePlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder
    label = "Collect Workfile"
    hosts = ['nuke']
    families = ["workfile"]

    def process(self, instance):  # sourcery skip: avoid-builtin-shadow

        script_data = instance.context.data["scriptData"]
        current_file = os.path.normpath(nuke.root().name())

        # hornet: check for timestamped workfile
        # creating instances per write node

        staging_dir = os.path.dirname(current_file)
        base_name = os.path.basename(current_file)
        submission_staging_dir = os.path.join(staging_dir, "submission")
        timestamp_regex = r'\d{4}-\d{2}-\d{2}\_\d{2}-\d{2}-\d{2}\.nk'
        nukeScripts = [f for f in os.listdir(staging_dir + '/submission') if f.endswith('.nk')]
        self.log.info(len(nukeScripts))
        timestampedScripts = [(f,re.search(timestamp_regex,f).group(0)[:-3]) for f in nukeScripts if re.search(timestamp_regex, f)]
        print(timestampedScripts)
        self.log.info(len(timestampedScripts))
        newest_file = None
        newest_timestamp = None
        if len(timestampedScripts) > 0:
            self.log.info("found timestamped workfiles in staging dir, submitting the latest")
            for filename, timestamp_str in timestampedScripts:
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d_%H-%M-%S')
                    if newest_timestamp is None or timestamp > newest_timestamp:
                        newest_timestamp = timestamp
                        newest_file = os.path.join(submission_staging_dir, filename)
                except ValueError:
                    self.log.info("Skipping file {filename}: Invalid timestamp format".format(filename=filename))
        if newest_file and os.path.exists(newest_file):
            base_name = newest_file
            self.log.info("Using {base_name} as workfile".format(base_name=base_name))
            if instance.context.data['cleanupFullPaths']: instance.context.data['cleanupFullPaths'].append(os.path.join(submission_staging_dir, filename))
            else: instance.context.data['cleanupFullPaths'] = [os.path.join(submission_staging_dir, filename)]
            representation = {
                'name': 'nk',
                'ext': 'nk',
                'files': base_name,
                "stagingDir": submission_staging_dir
            }
        # creating representation
        if not representation:
            representation = {
                'name': 'nk',
                'ext': 'nk',
                'files': base_name,
                "stagingDir": staging_dir,
            }

        # creating instance datas
        instance.data.update({
            "name": base_name,
            "representations": [representation]
        })
        # adding basic script data
        instance.data.update(script_data)

        self.log.debug(
            "Collected current script version: {}".format(current_file)
        )
