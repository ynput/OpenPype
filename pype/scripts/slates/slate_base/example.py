# import sys
# sys.append(r"PATH/TO/PILLOW/PACKAGE")

from . import api


def example():
    """Example data to demontrate function.

    It is required to fill "destination_path", "thumbnail_path"
    and "color_bar_path" in `example_fill_data` to be able to execute.
    """

    example_fill_data = {
        "destination_path": "PATH/TO/OUTPUT/FILE",
        "project": {
            "name": "Testing project"
        },
        "intent": "WIP",
        "version_name": "seq01_sh0100_compositing_v01",
        "date": "2019-08-09",
        "shot_type": "2d comp",
        "submission_note": (
            "Lorem ipsum dolor sit amet, consectetuer adipiscing elit."
            " Aenean commodo ligula eget dolor. Aenean massa."
            " Cum sociis natoque penatibus et magnis dis parturient montes,"
            " nascetur ridiculus mus. Donec quam felis, ultricies nec,"
            " pellentesque eu, pretium quis, sem. Nulla consequat massa quis"
            " enim. Donec pede justo, fringilla vel,"
            " aliquet nec, vulputate eget, arcu."
        ),
        "thumbnail_path": "PATH/TO/THUMBNAIL/FILE",
        "color_bar_path": "PATH/TO/COLOR/BAR/FILE",
        "vendor": "Our Studio",
        "shot_name": "sh0100",
        "frame_start": 1001,
        "frame_end": 1004,
        "duration": 3
    }

    example_presets = {"example_HD": {
        "width": 1920,
        "height": 1080,
        "destination_path": "{destination_path}",
        "style": {
            "*": {
                "font-family": "arial",
                "font-color": "#ffffff",
                "font-bold": False,
                "font-italic": False,
                "bg-color": "#0077ff",
                "alignment-horizontal": "left",
                "alignment-vertical": "top"
            },
            "layer": {
                "padding": 0,
                "margin": 0
            },
            "rectangle": {
                "padding": 0,
                "margin": 0,
                "bg-color": "#E9324B",
                "fill": True
            },
            "main_frame": {
                "padding": 0,
                "margin": 0,
                "bg-color": "#252525"
            },
            "table": {
                "padding": 0,
                "margin": 0,
                "bg-color": "transparent"
            },
            "table-item": {
                "padding": 5,
                "padding-bottom": 10,
                "margin": 0,
                "bg-color": "#212121",
                "bg-alter-color": "#272727",
                "font-color": "#dcdcdc",
                "font-bold": False,
                "font-italic": False,
                "alignment-horizontal": "left",
                "alignment-vertical": "top",
                "word-wrap": False,
                "ellide": True,
                "max-lines": 1
            },
            "table-item-col[0]": {
                "font-size": 20,
                "font-color": "#898989",
                "font-bold": True,
                "ellide": False,
                "word-wrap": True,
                "max-lines": None
            },
            "table-item-col[1]": {
                "font-size": 40,
                "padding-left": 10
            },
            "#colorbar": {
                "bg-color": "#9932CC"
            }
        },
        "items": [{
            "type": "layer",
            "direction": 1,
            "name": "MainLayer",
            "style": {
                "#MainLayer": {
                    "width": 1094,
                    "height": 1000,
                    "margin": 25,
                    "padding": 0
                },
                "#LeftSide": {
                    "margin-right": 25
                }
            },
            "items": [{
                "type": "layer",
                "name": "LeftSide",
                "items": [{
                    "type": "layer",
                    "direction": 1,
                    "style": {
                        "table-item": {
                            "bg-color": "transparent",
                            "padding-bottom": 20
                        },
                        "table-item-col[0]": {
                            "font-size": 20,
                            "font-color": "#898989",
                            "alignment-horizontal": "right"
                        },
                        "table-item-col[1]": {
                            "alignment-horizontal": "left",
                            "font-bold": True,
                            "font-size": 40
                        }
                    },
                    "items": [{
                        "type": "table",
                        "values": [
                            ["Show:", "{project[name]}"]
                        ],
                        "style": {
                            "table-item-field[0:0]": {
                                "width": 150
                            },
                            "table-item-field[0:1]": {
                                "width": 580
                            }
                        }
                    }, {
                        "type": "table",
                        "values": [
                            ["Submitting For:", "{intent}"]
                        ],
                        "style": {
                            "table-item-field[0:0]": {
                                "width": 160
                            },
                            "table-item-field[0:1]": {
                                "width": 218,
                                "alignment-horizontal": "right"
                            }
                        }
                    }]
                }, {
                    "type": "rectangle",
                    "style": {
                        "bg-color": "#bc1015",
                        "width": 1108,
                        "height": 5,
                        "fill": True
                    }
                }, {
                    "type": "table",
                    "use_alternate_color": True,
                    "values": [
                        ["Version name:", "{version_name}"],
                        ["Date:", "{date}"],
                        ["Shot Types:", "{shot_type}"],
                        ["Submission Note:", "{submission_note}"]
                    ],
                    "style": {
                        "table-item": {
                            "padding-bottom": 20
                        },
                        "table-item-field[0:1]": {
                            "font-bold": True
                        },
                        "table-item-field[3:0]": {
                            "word-wrap": True,
                            "ellide": True,
                            "max-lines": 4
                        },
                        "table-item-col[0]": {
                            "alignment-horizontal": "right",
                            "width": 150
                        },
                        "table-item-col[1]": {
                            "alignment-horizontal": "left",
                            "width": 958
                        }
                    }
                }]
            }, {
                "type": "layer",
                "name": "RightSide",
                "items": [{
                    "type": "placeholder",
                    "name": "thumbnail",
                    "path": "{thumbnail_path}",
                    "style": {
                        "width": 730,
                        "height": 412
                    }
                }, {
                    "type": "placeholder",
                    "name": "colorbar",
                    "path": "{color_bar_path}",
                    "return_data": True,
                    "style": {
                        "width": 730,
                        "height": 55
                    }
                }, {
                    "type": "table",
                    "use_alternate_color": True,
                    "values": [
                        ["Vendor:", "{vendor}"],
                        ["Shot Name:", "{shot_name}"],
                        ["Frames:", "{frame_start} - {frame_end} ({duration})"]
                    ],
                    "style": {
                        "table-item-col[0]": {
                            "alignment-horizontal": "left",
                            "width": 200
                        },
                        "table-item-col[1]": {
                            "alignment-horizontal": "right",
                            "width": 530,
                            "font-size": 30
                        }
                    }
                }]
            }]
        }]
    }}

    api.create_slates(example_fill_data, "example_HD", example_presets)
