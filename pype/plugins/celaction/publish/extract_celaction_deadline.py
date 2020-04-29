import os

import pyblish.api
import pyblish_standalone
import clique
import requests
from bait.deadline import get_render_settings, get_deadline_data, format_frames
from bait.paths import get_output_path


class ExtractCelactionDeadline(pyblish.api.InstancePlugin):

    label = 'Deadline'
    families = ['render']
    order = pyblish.api.ExtractorOrder

    def process(self, instance):

        render_settings = get_render_settings("celaction")

        existing_data = instance.data.get(
            "deadlineData", {"job": {}, "plugin": {}}
        )

        task_id = instance.context.data["ftrackData"]["Task"]["id"]

        data = get_deadline_data(render_settings, existing_data)

        filename = os.path.basename(instance.context.data["currentFile"])
        filename_no_ext, ext = os.path.splitext(filename)

        data["job"]["Name"] = filename_no_ext + " - " + instance.data["name"]
        data["job"]['Frames'] = format_frames(
            instance.data('start'), instance.data('end'))

        # get version data
        version = instance.context.data(
            'version') if instance.context.has_data('version') else 1

        output_path = get_output_path(
            task_id, instance.data["name"], version, "png")
        output_path = output_path.replace("/", "\\")

        data['job']['Plugin'] = 'CelAction'
        data['job']["BatchName"] = filename
        data['job']["UserName"] = os.environ['USERNAME']
        data["job"]['OutputFilename0'] = output_path.replace('%04d', '####')

        scene_path = pyblish_standalone.kwargs['path'][0]
        scene_path = scene_path.replace("/", "\\")
        _, ext = os.path.splitext(scene_path)

        # plugin data
        self.log.info(scene_path)

        args = '<QUOTE>{}<QUOTE>'.format(scene_path)
        args += ' -a'
        args += ' -8'
        args += ' -s <STARTFRAME>'
        args += ' -e <ENDFRAME>'
        args += ' -d <QUOTE>{}<QUOTE>'.format(os.path.dirname(output_path))
        args += ' -x {}'.format(instance.data('x'))
        args += ' -y {}'.format(instance.data('y'))
        args += ' -r <QUOTE>{}<QUOTE>'.format(output_path.replace('.%04d', ''))
        args += ' -= AbsoluteFrameNumber=on -= PadDigits=4'
        args += ' -= ClearAttachment=on'

        data["plugin"]['StartupDirectory'] = ''
        data["plugin"]['Arguments'] = args

        self.log.info(data)

        head = output_path.replace('%04d', '')
        tail = ".png"
        collection = clique.Collection(head=head, padding=4, tail=tail)

        frame_start = int(instance.data['start'])
        frame_end = int(instance.data['end'])

        for frame_no in range(frame_start, frame_end):
            collection.add(head + str(frame_no).zfill(4) + tail)

        # instance.data["collection"] = collection

        # adding to instance
        instance.set_data('deadlineData2', value=data)
        # instance.set_data('deadlineSubmissionJob', value=data)

        payload = {
            "JobInfo": data["job"],
            "PluginInfo": data["plugin"],
            "AuxFiles": []
        }

        url = "{}/api/jobs".format('http://192.168.146.8:8082')
        response = requests.post(url, json=payload)
        if not response.ok:
            raise Exception(response.text)

        # Store output dir for unified publisher (filesequence)
        instance.data["outputDir"] = os.path.dirname(
            data["job"]['OutputFilename0'])
        instance.data["deadlineSubmissionJob"] = response.json()

        instance.context.data['ftrackStatus'] = "Render"

        # creating output path
        if not os.path.exists(os.path.dirname(output_path)):
            os.makedirs(os.path.dirname(output_path))
