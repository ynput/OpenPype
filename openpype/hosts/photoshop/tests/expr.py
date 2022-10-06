import json

data = [
    {
        "schema": "openpype:container-2.0",
        "id": "pyblish.avalon.container",
        "name": "imageArtNeew",
        "namespace": "Jungle_imageArtNeew_001",
        "loader": "ReferenceLoader",
        "representation": "61c1eb91e1a4d1e5a23582f6",
        "members": [
            "131"
        ]
    },
    {
        "id": "pyblish.avalon.instance",
        "family": "image",
        "asset": "Jungle",
        "subset": "imageMainBg",
        "active": True,
        "variant": "Main",
        "uuid": "199",
        "long_name": "BG"
    },
    {
        "id": "pyblish.avalon.instance",
        "family": "image",
        "asset": "Jungle",
        "subset": "imageMain",
        "active": True,
        "variant": "Main",
        "uuid": "192",
        "long_name": "imageMain"
    },
    {
        "id": "pyblish.avalon.instance",
        "family": "workfile",
        "subset": "workfile",
        "active": True,
        "creator_identifier": "workfile",
        "asset": "Jungle",
        "task": "art",
        "variant": "",
        "instance_id": "3ed19342-cd8e-4bb6-8cda-d6e74d9a7efe",
        "creator_attributes": {},
        "publish_attributes": {}
    }
]

with open("C:\\Users\\petrk\\PycharmProjects\\Pype3.0\\pype\\openpype\\hosts\\photoshop\\tests\\mock_get_layers_metadata.json", 'w') as fp:
    fp.write(json.dumps(data, indent=4))