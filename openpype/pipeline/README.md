# Colorspace
1. Each host handling pixle data is requiring setting schema.
```json
{
    "key": "imageio",
    "type": "dict",
    "label": "Color Management (ImageIO)",
    "is_group": true,
    "children": [
        {
            "type": "schema",
            "name": "schema_imageio_config"
        },
        {
            "type": "schema",
            "name": "schema_imageio_file_rules"
        }

    ]
}
```

1. Use any mechanism to set OCIO config to host app resolved from `openpype\pipeline\colorspace.py:get_imageio_config`
	-	either set OCIO environment during host launching via pre-launch hook
	- or to set workfile ocio config path if host api is available

2. Each pixle related exporter plugins has to use parent class `openpype\pipeline\publish\publish_plugins.py:ExtractorColormanaged` and use it similarly as it is already implemented here `openpype\hosts\nuke\plugins\publish\extract_render_local.py`
- **get_colorspace_settings**: is solving all settings for the host context
- **set_representation_colorspace**: is adding colorspaceData to representation. If the colorspace is known then it is added directly to the representation with resolved config path.
