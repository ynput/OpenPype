from slate_base import api
import sys
import json

if __package__:
    from .slate_base import api
else:
    from slate_base import api


def main(in_args=None):
    data_arg = in_args[-1]
    in_data = json.loads(data_arg)
    api.slate_generator(
        in_data["fill_data"],
        in_data["slate_settings"],
        in_data["output_path"],
        in_data.get("width"),
        in_data.get("height"),
        in_data.get("fonts_dir")
    )


if __name__ == "__main__":
    main(sys.argv)
