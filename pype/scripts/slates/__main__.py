import sys
import json
from slate_base import api


def main(in_args=None):
    data_arg = in_args[-1]
    in_data = json.loads(data_arg)
    api.create_slates(
        in_data["fill_data"],
        in_data.get("slate_name"),
        in_data.get("slate_data"),
        in_data.get("data_output_json")
    )


if __name__ == "__main__":
    main(sys.argv)
