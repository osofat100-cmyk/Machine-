"""Start day_server.py on a free port, talk to it, and always shut it down (terminate + wait)."""
import http.client
import json
import os
import socket
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


class Server:
    def __init__(self, file=None):
        self.file = file

    def __enter__(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        cmd = [sys.executable, os.path.join(HERE, "day_server.py"), "--port", str(self.port)]
        if self.file:
            cmd += ["--file", self.file]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
        line = self.proc.stdout.readline()
        if not line.startswith("ready"):
            self.proc.kill()
            raise RuntimeError(f"day server did not start: {line!r}")
        self.conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        return self

    def next(self, orders):
        body = json.dumps({"orders": orders})
        self.conn.request("POST", "/next", body=body, headers={"Content-Type": "application/json"})
        r = self.conn.getresponse()
        data = json.loads(r.read())
        if r.status != 200:
            raise RuntimeError(data)
        return data

    def __exit__(self, *exc):
        self.conn.close()
        self.proc.terminate()
        self.proc.wait(timeout=30)
