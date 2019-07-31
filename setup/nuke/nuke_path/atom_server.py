'''
    Simple socket server using threads
'''

import socket
import sys
import threading
import StringIO
import contextlib

import nuke

HOST = ''
PORT = 8888


@contextlib.contextmanager
def stdoutIO(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = StringIO.StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old


def _exec(data):
    with stdoutIO() as s:
        exec(data)
    return s.getvalue()


def server_start():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(5)

    while 1:
        client, address = s.accept()
        try:
            data = client.recv(4096)
            if data:
                result = nuke.executeInMainThreadWithResult(_exec, args=(data))
                client.send(str(result))
        except SystemExit:
            result = self.encode('SERVER: Shutting down...')
            client.send(str(result))
            raise
        finally:
            client.close()

t = threading.Thread(None, server_start)
t.setDaemon(True)
t.start()
