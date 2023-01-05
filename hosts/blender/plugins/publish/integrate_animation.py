import json

import pyblish.api


class IntegrateAnimation(pyblish.api.InstancePlugin):
    """Generate a JSON file for animation."""

    label = "Integrate Animation"
    order = pyblish.api.IntegratorOrder + 0.1
    optional = True
    hosts = ["blender"]
    families = ["setdress"]

    def process(self, instance):
        self.log.info("Integrate Animation")

        representation = instance.data.get('representations')[0]
        json_path = representation.get('publishedFiles')[0]

        with open(json_path, "r") as file:
            data = json.load(file)

        # Update the json file for the setdress to add the published
        # representations of the animations
        for json_dict in data:
            i = None
            for elem in instance.context:
                if elem.data.get('subset') == json_dict['subset']:
                    i = elem
                    break
            if not i:
                continue
            rep = None
            pub_repr = i.data.get('published_representations')
            for elem in pub_repr:
                if pub_repr.get(elem).get('representation').get('name') == "fbx":
                    rep = pub_repr.get(elem)
                    break
            if not rep:
                continue
            obj_id = rep.get('representation').get('_id')

            if obj_id:
                json_dict['_id'] = str(obj_id)

        with open(json_path, "w") as file:
            json.dump(data, fp=file, indent=2)
