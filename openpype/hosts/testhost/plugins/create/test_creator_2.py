from openpype.hosts.testhost import api
from openpype.pipeline import (
    Creator,
    CreatedInstance,
    lib
)


class TestCreatorTwo(Creator):
    family = "test_two"
    description = "A second testing creator"

    def get_icon(self):
        return "cube"

    def create(self, subset_name, data, options=None):
        avalon_instance = CreatedInstance(self.family, subset_name, data, self)
        api.pipeline.HostContext.add_instance(avalon_instance.data_to_store())
        self.log.info(avalon_instance.data)
        return avalon_instance

    def get_attribute_defs(self):
        output = [
            lib.NumberDef("number_key"),
            lib.TextDef("text_key")
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
