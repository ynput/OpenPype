from . import api

def example():
    """Example data to demontrate function.

    It is required to fill "destination_path", "thumbnail_path"
    and "color_bar_path" in `example_fill_data` to be able to execute.
    """

    example_fill_data = {
        "destination_path": "C:/CODE/_PYPE_testing/slates_testing/slate.png",
        "shot": "106_V12_010",
        "version": "V007",
        "length": 187,
        "date": "11/02/2021",
        "artist": "John Murdoch",
        "notes": (
            "Lorem ipsum dolor sit amet, consectetuer adipiscing elit."
            " Aenean commodo ligula eget dolor. Aenean massa."
            " Cum sociis natoque penatibus et magnis dis parturient montes,"
            " nascetur ridiculus mus. Donec quam felis, ultricies nec,"
            " pellentesque eu, pretium quis, sem. Nulla consequat massa quis"
            " enim. Donec pede justo, fringilla vel,"
            " aliquet nec, vulputate eget, arcu."
        ),
        "thumbnail_path": "C:/CODE/_PYPE_testing/slates_testing/thumbnail.png",
        "logo": "C:/CODE/_PYPE_testing/slates_testing/logo.jpg",
        "vendor": "VENDOR"
    }

    example_presets = {
        "width": 2048,
        "height": 1080,
        "destination_path": "{destination_path}",
        "style": {
            "*": {
                "font-family": "verdana",
                "font-color": "#ffffff",
                "font-bold": False,
                "font-italic": False
            },
            "layer": {
                "padding": 0,
                "margin": 0
            },
            "rectangle": {
                "padding": 0,
                "margin": 0,
                "fill": True
            },
            "main_frame": {
                "padding": 0,
                "margin": 30
            },
            "table": {
                "padding": 0,
                "margin-top": 30
            },
            "table-item": {
                "padding": 5,
                "padding-bottom": 20,
                "margin": 0,
                "bg-color": "transparent",
                "bg-alter-color": "transparent",
                "font-color": "#dcdcdc",
                "font-bold": True,
                "font-italic": False,
                "alignment-horizontal": "left",
                "alignment-vertical": "top",
                "word-wrap": True,
                "ellide": True,
                "max-lines": 2
            },
            "#MainLayer": {
                "margin": 0,
                "padding": 0,
                "min-width": 2048,
                "min-height": 1080,
                "alignment-horizontal": "center",
                "alignment-vertical": "center"
            },
            "#VendorLayer": {
                "margin": 0,
                "padding-right": 0,
                "min-width": 2048,
                "min-height": 1080,
                "alignment-horizontal": "right",
                "alignment-vertical": "center"
            },
            "#Thumbnail": {
                "margin-top": 50,
            }
        },
        "items": [{
            "type": "layer",
            "name": "MainLayer",
            "items": [{
                "type": "layer",
                "name": "Thumbnail",
                "items": [{
                    "type": "image",
                    "name": "thumbnail",
                    "path": "{thumbnail_path}",
                    "style": {
                        "width": 730,
                        "height": 412
                    }
                }]
            }, {
                "type": "layer",
                "name": "Metadata",
                "items": [{
                    "type": "table",
                    "use_alternate_color": True,
                    "values": [
                        ["SHOT", "{shot}"],
                        ["VERSION", "{version}"],
                        ["LENGTH", "{length}"],
                        ["DATE", "{date}"],
                        ["ARTIST", "{artist}"],
                        ["NOTES", "{notes}"]
                    ],
                    "style": {
                        "table-item": {
                            "padding": 0
                        },
                        "table-item-field[3:0]": {
                            "word-wrap": True,
                            "ellide": True,
                            "max-lines": 4
                        },
                        "table-item-col[0]": {
                            "font-size": 30,
                            "font-color": "#527ce8",
                            "font-bold": False,
                            "ellide": False,
                            "word-wrap": True,
                            "max-lines": None,
                            "alignment-horizontal": "right",
                            "width": 200
                        },
                        "table-item-col[1]": {
                            "font-size": 30,
                            "padding-left": 10,
                            "alignment-horizontal": "left",
                            "width": 800
                        }
                    }
                }]
            }]
        }, {
            "type": "layer",
            "name": "VendorLayer",
            "items": [
                    {
                        "type": "table",
                        "values": [
                            ["{vendor}"]
                        ],
                        "style": {
                            "table-item-col[0]": {
                                "font-size": 50,
                                "margin-right": 50,
                                "font-color": "#ffffff",
                                "alignment-horizontal": "right",
                                "width": 500,
                                "bg-color": "#527ce8"
                            }
                        }
                    }
            ]
        }]
    }

    api.create_slates(example_fill_data, example_presets)
