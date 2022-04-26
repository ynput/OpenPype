from openpype.lib import NumberDef, TextDef
from openpype.hosts.testhost.api import pipeline
from openpype.pipeline import (
    Creator,
    CreatedInstance,
)


class TestCreatorTwo(Creator):
    identifier = "test_two"
    label = "test"
    family = "test"
    description = "A second testing creator"

    def get_icon(self):
        return "cube"

    def create(self, subset_name, data, pre_create_data):
        new_instance = CreatedInstance(self.family, subset_name, data, self)
        pipeline.HostContext.add_instance(new_instance.data_to_store())
        self.log.info(new_instance.data)
        self._add_instance_to_context(new_instance)

    def collect_instances(self):
        for instance_data in pipeline.list_instances():
            creator_id = instance_data.get("creator_identifier")
            if creator_id == self.identifier:
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )
                self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        pipeline.update_instances(update_list)

    def remove_instances(self, instances):
        pipeline.remove_instances(instances)
        for instance in instances:
            self._remove_instance_from_context(instance)

    def get_instance_attr_defs(self):
        output = [
            NumberDef("number_key"),
            TextDef("text_key")
        ]
        return output

    def get_detail_description(self):
        return """# Lorem ipsum, dolor sit amet. [![Awesome](https://cdn.rawgit.com/sindresorhus/awesome/d7305f38d29fed78fa85652e3a63e154dd8e8829/media/badge.svg)](https://github.com/sindresorhus/awesome)

> A curated list of awesome lorem ipsum generators.

Inspired by the [awesome](https://github.com/sindresorhus/awesome) list thing.


## Table of Contents

- [Legend](#legend)
- [Practical](#briefcase-practical)
- [Whimsical](#roller_coaster-whimsical)
    - [Animals](#rabbit-animals)
    - [Eras](#tophat-eras)
    - [Famous Individuals](#sunglasses-famous-individuals)
    - [Music](#microphone-music)
    - [Food and Drink](#pizza-food-and-drink)
    - [Geographic and Dialects](#earth_africa-geographic-and-dialects)
    - [Literature](#books-literature)
    - [Miscellaneous](#cyclone-miscellaneous)
    - [Sports and Fitness](#bicyclist-sports-and-fitness)
    - [TV and Film](#movie_camera-tv-and-film)
- [Tools, Apps, and Extensions](#wrench-tools-apps-and-extensions)
- [Contribute](#contribute)
- [TODO](#todo)
"""
