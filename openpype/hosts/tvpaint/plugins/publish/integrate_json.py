import json
import re

import pyblish.api


class IntegrateJson(pyblish.api.InstancePlugin):
    """Integrate a JSON file."""

    label = "Integrate Json File"
    order = pyblish.api.IntegratorOrder + 0.05

    hosts = ["tvpaint"]
    families = ["renderLayer"]

    def process(self, instance):
        self.log.info(
            "* Processing instance \"{}\"".format(instance.data["label"])
        )

        if not instance.data.get('json_output_dir'):
            return

        for repre in instance.data.get("representations"):
            if repre['name'] != 'png' or 'review' in repre['tags']:
                continue

            published_layer_data = self._update_with_published_file(
                instance.data['layers_data'],
                repre['published_path']
            )

            json_repre = self._get_json_repre(instance.context)

            json_publish_path = json_repre['published_path']
            with open(json_publish_path, "r+") as publish_json:
                published_data = json.load(publish_json)

                published_data['project']['clip']['layers'].append(
                    published_layer_data
                )
                publish_json.seek(0)
                json.dump(published_data, publish_json, indent=4)
                publish_json.truncate()

            self.log.debug('Add layer_data to Json file: {}'.format(
                json_publish_path
            ))

    def _update_with_published_file(self, layer_data, publish_path):
        """Update published file path in the json file extracted.
        """
        for link in layer_data['link']:
            link_frame = re.search(r'\.(\d*)\.png$', link['file']).groups()[0]
            new_file_path = re.sub(
                r'(.*\.)(\d*)(\.png)$',
                '\g<1>{}\g<3>'.format(link_frame),
                publish_path
            )
            link['file'] = new_file_path

        self.log.debug("Updated layer_data: {}".format(layer_data))
        return layer_data

    def _get_json_repre(self, context):
        """Get the json representation of the instance.
        Raises error if more than one representation is found.
        """
        json_repre = []
        for instance in context:
            repres = instance.data.get("representations")
            for repre in repres:
                if repre['name'] != 'json':
                    continue
                json_repre.append(repre)

        if len(json_repre) != 1:
            raise Exception(
                'Exporting multiple json is not supported: {}'.format(
                    json_repre
                )
            )

        return json_repre[0]
