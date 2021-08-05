from . import api


def example():
    """Example data to demontrate function.

    It is required to fill "destination_path", "thumbnail_path"
    and "color_bar_path" in `example_fill_data` to be able to execute.
    """

    example_fill_data = {
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
        "style": {
            "*": {
                "font-family": "verdana",
                "font-color": "#ffffff",
                "font-bold": False,
                "font-italic": False,
                "segments": 20
            },
            "layer": {
                "padding": 0,
                "margin": 0
            },
            "text": {
                "padding": 0,
                "margin": 0
            },
            "rectangle": {
                "fill": True
            },
            "main_frame": {
                "bg-color": "#393939",
                "margin": 0.1
            },
            "table": {
                "margin-top": 0.3,
                "margin-right": 4
            },
            "table-item": {
                "padding": 0.5,
                "padding-bottom": 0.1,
                "bg-color": "transparent",
                "bg-alter-color": "transparent",
                "font-color": "#dcdcdc",
                "font-bold": True,
                "font-italic": False,
                "alignment-horizontal": "left",
                "alignment-vertical": "top",
                "word-wrap": True,
                "ellide": True,
                "max-lines": 1
            },
            "#MainLayer": {
                "min-width": 20,
                "min-height": "root-ratio",
                "alignment-horizontal": "center",
                "alignment-vertical": "center"
            },
            "#VendorLayer": {
                "min-width": 20,
                "min-height": "root-ratio",
                "alignment-horizontal": "right"
            },
            "#Thumbnail": {
                "margin-top": 0.6
            },
            "#LogoLayer": {
                "min-width": 20,
                "min-height": "root-ratio",
                "alignment-horizontal": "left"
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
                            "width": 8,
                            "height": "img-ratio"
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
                            "padding": 0.01
                        },
                        "table-item-field[5:1]": {
                            "word-wrap": True,
                            "ellide": True,
                            "max-lines": 4
                        },
                        "table-item-col[0]": {
                            "font-size": 0.3,
                            "font-color": "#527ce8",
                            "font-bold": False,
                            "ellide": False,
                            "word-wrap": True,
                            "max-lines": None,
                            "alignment-horizontal": "right",
                            "width": 2
                        },
                        "table-item-col[1]": {
                            "font-size": 0.3,
                            "padding-left": 0.1,
                            "alignment-horizontal": "left",
                            "width": 9
                        }
                    }
                }]
            }]
        }, {
            "type": "layer",
            "name": "VendorLayer",
            "items": [
                    {
                        "type": "rectangle",
                        "style": {
                                "width": 20,
                                "height": "90%",
                                "bg-color": "transparent"
                        }
                    }, {
                        "type": "text",
                        "value": "{vendor}",
                        "name": "vendorText",
                        "style": {
                                "padding-left": -1,
                                "font-size": .5,
                                "font-color": "#ffffff",
                                "bg-color": "transparent",
                                "font-bold": True
                        }
                    }
            ]
        }, {
            "type": "layer",
            "name": "LogoLayer",
            "items": [
                    {
                        "type": "rectangle",
                        "style": {
                                "width": 20,
                                "height": "70%",
                                "bg-color": "transparent"
                        }
                    }, {
                        "type": "image",
                        "name": "logo",
                        "path": "{logo}",
                        "style": {
                                "padding-left": .8,
                                "width": 3,
                                "height": "img-ratio"
                        }
                    }
            ]
        }]
    }

    api.slate_generator(
        example_fill_data, example_presets,
        output_path="C:/CODE/_PYPE_testing/slates_testing/slate.png",
        # width=2048, height=1080
    )
