# Python script to send data using sockets

import socket
import json


def send_message_to_OpenPype(data_to_send):
    # Serialize the Python dictionary into a JSON string
    data_json = json.dumps(data_to_send)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ("localhost", 12345)
    client_socket.connect(server_address)
    client_socket.send(data_json.encode())
    client_socket.close()


# Variable data is passed from openpype_menu.fu
if "menu_item" in data and "uuid" in data:
    send_message_to_OpenPype(data)
else:
    print(
        f"data sent didn't contain all needed items (menu_item and uuid):"
        f"\n{data}"
    )
