import sys
import json

from ayon_common.connection.ui.login_window import ask_to_login


def main(output_path):
    with open(output_path, "r") as stream:
        data = json.load(stream)

    url = data.get("url")
    username = data.get("username")
    always_on_top = data.get("always_on_top", False)
    out_url, out_token, out_username = ask_to_login(
        url, username, always_on_top=always_on_top)

    data["output"] = [out_url, out_token, out_username]
    with open(output_path, "w") as stream:
        json.dump(data, stream)


if __name__ == "__main__":
    main(sys.argv[-1])
