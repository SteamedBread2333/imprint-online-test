#!/usr/bin/env python3
"""Minimal MCP stdio client to drive the real `imprint-mcp` server.

Speaks standard MCP (JSON-RPC 2.0 over newline-delimited stdio).
Used by the "with-memory" scenario so that find/add go through the actual
imprint-mcp server process (not the CLI), producing a real vault.db.
"""
import json
import os
import subprocess
import sys
import threading
import queue

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PROTOCOL_VERSION = "2024-11-05"


class MCPClient:
    def __init__(self, command, args, cwd):
        self.proc = subprocess.Popen(
            [command] + args,
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._q = queue.Queue()
        self._next_id = 0
        self._lock = threading.Lock()
        self.stderr_lines = []
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._stderr_reader, daemon=True).start()

    def _reader(self):
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._q.put(json.loads(line))
            except json.JSONDecodeError:
                self._q.put({"raw": line})

    def _stderr_reader(self):
        for line in self.proc.stderr:
            self.stderr_lines.append(line.rstrip("\n"))

    def request(self, method, params=None, timeout=120.0):
        with self._lock:
            self._next_id += 1
            req_id = self._next_id
            msg = {"jsonrpc": "2.0", "id": req_id, "method": method,
                   "params": params or {}}
            self.proc.stdin.write(json.dumps(msg) + "\n")
            self.proc.stdin.flush()
        deadline = timeout
        import time
        t0 = time.time()
        while time.time() - t0 < deadline:
            try:
                msg = self._q.get(timeout=deadline)
            except queue.Empty:
                raise TimeoutError(f"no response for {method} within {timeout}s")
            if msg.get("id") == req_id:
                return msg
        raise TimeoutError(f"no matching response for {method}")

    def notify(self, method, params=None):
        msg = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def initialize(self):
        result = self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "imprint-token-benchmark", "version": "1.0.0"},
        })
        self.notify("notifications/initialized")
        return result

    def list_tools(self):
        return self.request("tools/list")

    def call_tool(self, name, arguments):
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--vault", default=".imprint")
    from paths import imprint_mcp
    p.add_argument("--bin", default=imprint_mcp(),
                   help="path to imprint-mcp binary")
    p.add_argument("--smoke", action="store_true",
                   help="only do initialize + tools/list and print tool names")
    args = p.parse_args()

    client = MCPClient(args.bin, ["--project", args.project,
                                  "--vault", args.vault], cwd=args.project)
    try:
        init_resp = client.initialize()
        print("== initialize OK ==")
        print(json.dumps(init_resp.get("result", {}).get("serverInfo", {}),
                         ensure_ascii=False))
        tl = client.list_tools()
        tools = tl.get("result", {}).get("tools", [])
        print(f"== tools/list: {len(tools)} tools ==")
        for t in tools:
            print(" -", t.get("name"), "::", t.get("description", "")[:60])
    finally:
        client.close()
    if client.stderr_lines:
        print("== stderr (last 10) ==")
        for l in client.stderr_lines[-10:]:
            print(" ", l)


if __name__ == "__main__":
    main()