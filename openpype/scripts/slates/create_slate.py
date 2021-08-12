import sys
import json
from slate_base import api

if __name__ == "__main__":
    print("* Slate generator started")
    in_data_json_path = sys.argv[-1]
    with open(in_data_json_path, "r") as file_stream:
        in_data = json.load(file_stream)

    api.slate_generator(
        in_data["fill_data"],
        in_data["slate_settings"],
        in_data["output_path"],
        in_data.get("width"),
        in_data.get("height"),
        in_data.get("fonts_dir")
    )
